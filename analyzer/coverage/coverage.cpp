#include "pin.H"

#include <stdio.h>
#include <errno.h>

#ifdef TARGET_LINUX

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#elif TARGET_WINDOWS
namespace WIN32_API {
    #include <Windows.h>
}
#endif

/* Definitions of pintool's data structures. */

// struct that holds information
// about an image.
typedef struct
{
    ADDRINT low;
    ADDRINT high;
    INT32 loaded;
    char *path;
    UINT32 index;
} image_t;

// whitelist type
typedef struct
{
    image_t *list;
    off_t len;
} whitelist_t;

typedef struct {
    UINT64 image_index;
    UINT64 bbl;
} node_t;

typedef struct 
{
    UINT64 size;
    node_t *start;
    node_t *curr; // points to the first *empty* node
    node_t *end; // points right *after* the allocated region
    UINT32 guard;
} bucket_t;

/* Declaration of global variables */
uint64_t bbls_count;
#ifdef TARGET_LINUX
int pipeHandle;
#elif TARGET_WINDOWS
WIN32_API::HANDLE pipeHandle;
WIN32_API::HANDLE TimeoutEvent;
volatile WIN32_API::BOOL IsProcessRunning = true;
volatile WIN32_API::BOOL IsProcessSignaled = false;
PIN_LOCK *PinThreadLock;
PIN_THREAD_UID InternalPINThreadUid;
#else
#error "This operating system is not supported yet."
#endif

#define IS_BUCKET_FULL(bkt) (bkt->curr > bkt->end)
bucket_t *bucket;
whitelist_t whitelist;

VOID write_to_pipe(VOID *, size_t);

bucket_t *
init_bucket(int pipe_size)
{
    bucket_t *bkt = (bucket_t *)malloc(sizeof(bucket_t));
    if(bkt == NULL)
    {
        perror("malloc");
        return NULL;
    }

    bkt->size = (pipe_size >> 1) / sizeof(node_t);
    bkt->start = bkt->curr = (node_t *)malloc(bkt->size * sizeof(node_t));
    bkt->end = bkt->start + bkt->size;
    bkt->guard = 0x41424344;
    if(bkt->start == NULL)
    {
        perror("malloc");
        return NULL;
    }
    return bkt;
}

/* Whitelisting */
INT32
wht_insert_image(image_t *image)
{
    image_t *list = whitelist.list;
    off_t i = 0;
    for (i=0; i < whitelist.len; i++)
    {
        char *stub = (char *)strstr(
                image->path,
                list[i].path
                );

        // search other
        if (stub == NULL)
            continue;

        image->index = i;
        // copy image metadata to whitelist
        memcpy(list+i, image, sizeof(image_t));
        return 0;
    }

    return -1;
}

image_t *
wht_find_image(ADDRINT bbl)
{
    image_t *list = whitelist.list;
    off_t i = 0;
    for (i=0; i < whitelist.len; i++)
    {
        if (!list[i].loaded)
            continue;

        if (list[i].low <= bbl && list[i].high >= bbl)
           return list+i;
    }

    return NULL;
}

/*
 * Initializes the whitelist struct and fills
 * it with image stubs.
 *
 * wht_insert_image() whill overwrite the matching
 * stub with the loaded image.
 */
VOID
wht_init(KNOB<std::string> *img_list)
{
    // Initialize the whitelist structure
    // set the length and allocate the space
    // required.
    whitelist.len = img_list->NumberOfValues();
    whitelist.list = (image_t *)malloc(
            whitelist.len * sizeof(image_t)
            );

    // TODO: needs some better error
    // handling.
    if (!whitelist.list)
        LOG("Could not allocate whitelist\n");

    // build an empty stub that
    // will be overwritten by the 
    // matching image if that image
    // is loaded.
    image_t *p;
    off_t i = 0;
    image_t stub;

    stub.low = 0;
    stub.high = 0;
    stub.loaded = 0;
    stub.path = NULL;

    for (i=0; i < whitelist.len; i++)
    {
        stub.path = (char *)img_list->Value(i).c_str();
        stub.index = i;
        p = whitelist.list + i;
        memcpy(p, &stub, sizeof(image_t));
    }
}

VOID
wht_free()
{
    free(whitelist.list);
}

/* Instrumentation */
VOID
img_load(IMG img, VOID *v)
{
    image_t image;
    image.path = (char *)IMG_Name(img).c_str();
    image.low = IMG_LowAddress(img);
    image.high = IMG_HighAddress(img);
    image.loaded = 1;

    LOG("[+] Image ");
    LOG(image.path);
    if(!wht_insert_image(&image))
        LOG("loaded successfully\n");
    else
        LOG("skipped\n");
}

VOID 
img_unload(IMG img, VOID *v)
{
    ADDRINT low = IMG_LowAddress(img);
    image_t *i = wht_find_image(low);
    if (i)
    {
        LOG("[+] Unloading image ");
        LOG(i->path);
        LOG("\n");
        i->loaded = 0;
    }
}

VOID 
bbl_hit_handler(image_t *img, ADDRINT ip)
{
#ifdef TARGET_WINDOWS
    PIN_GetLock(PinThreadLock, 0);
    if(IsProcessSignaled)
        return;
#endif /* TARGET_WINDOWS */

    if(IS_BUCKET_FULL(bucket))
    {
        write_to_pipe(bucket->start, (bucket->end - bucket->start) * sizeof(node_t));
        bucket->curr = bucket->start;
    }

    bucket->curr->image_index = img->index;
    bucket->curr->bbl = (UINT64)(ip - img->low);
    bucket->curr++;

    bbls_count++;

#ifdef TARGET_WINDOWS
    PIN_ReleaseLock(PinThreadLock);
#endif /* TARGET_WINDOWS */
}

VOID
trace_callback(TRACE trace, VOID *v)
{
    // get trace's address and check
    // if the image it belongs to has
    // been whitelisted.
    ADDRINT addr = TRACE_Address(trace);
    image_t *im = wht_find_image(addr);
    if (!im)
        return;

    // add instrumentation to all basic blocks
    // in the current trace.
    BBL bbl = TRACE_BblHead(trace);
    for (; BBL_Valid(bbl); bbl = BBL_Next(bbl))
    {
        addr = BBL_Address(bbl);

        // enable tracing of this
        // basic block.
        BBL_InsertCall(
                bbl,
                IPOINT_ANYWHERE,
                (AFUNPTR)bbl_hit_handler,
                IARG_FAST_ANALYSIS_CALL,
                IARG_PTR,
                im,
                IARG_ADDRINT,
                addr,
                IARG_END
                );
    }
}

void
context_change_cb(THREADID thridx, CONTEXT_CHANGE_REASON reason, const CONTEXT *from, CONTEXT *to, INT32 info, VOID *v) 
{
    switch(reason)
    {
        case CONTEXT_CHANGE_REASON_FATALSIGNAL:
            if(IS_BUCKET_FULL(bucket))
            {
                write_to_pipe(bucket->start, (bucket->end - bucket->start) * sizeof(node_t));
                bucket->curr = bucket->start;
            }
            bucket->curr->image_index = 0xFFFFFFFFFFFFFFFF;
            bucket->curr->bbl = (UINT64)info;
            bucket->curr++;
            break;
        case CONTEXT_CHANGE_REASON_EXCEPTION:
            #define IS_FATAL_EXCEPTION(ex) ((ex & 0xC0000000) == 0xC0000000)
            if(IS_FATAL_EXCEPTION(info))
            {
                if(IS_BUCKET_FULL(bucket))
                {
                    write_to_pipe(bucket->start, (bucket->end - bucket->start) * sizeof(node_t));
                    bucket->curr = bucket->start;
                }
                bucket->curr->image_index = 0xFFFFFFFFFFFFFFFF;
                bucket->curr->bbl = (UINT64)info;
                bucket->curr++;
            }
            break;
        default:
            break;
    }
}

/* Windows specific code */
#ifdef TARGET_WINDOWS

#define EVENT_WAIT_TIMEOUT 500
/* Checks whether a time out event has been triggered. If that's the case
 * it flushes the data from buckets into the pipe and returns.
 */
void 
CheckTerminationEvent(void *arg)
{
    using namespace WIN32_API;
    LOG("New thread has spawned.\n");
    while(IsProcessRunning)
    {
        if(WaitForSingleObject(TimeoutEvent, EVENT_WAIT_TIMEOUT) == WAIT_OBJECT_0)
        {
            LOG("Event was set.\n");
            PIN_GetLock(PinThreadLock, 0);

            if(IS_BUCKET_FULL(bucket))
            {
                write_to_pipe(bucket->start, (bucket->end - bucket->start) * sizeof(node_t));
                bucket->curr = bucket->start;
            }
            bucket->curr->image_index = 0xFFFFFFFFFFFFFFFF;
            // SIGUSR2, process terminated due to a timeout event
            bucket->curr->bbl = (uint64_t)(0x0000000c);
            bucket->curr++;

            IsProcessSignaled = true;
            IsProcessRunning = false;
            PIN_ReleaseLock(PinThreadLock);
            PIN_ExitApplication(0);
        }
    }
}

/* Signal the interal pin thread that the process is exiting
 * wait the thread to terminate.
 */
VOID
TerminateInternalPINThreads(VOID *dummy)
{
    LOG("Waiting for CheckTerminiationEvent\n");
    IsProcessRunning = false;
    PIN_WaitForThreadTermination(InternalPINThreadUid, PIN_INFINITE_TIMEOUT, NULL);
    LOG("CheckTerminatioEvent has finished.\n");
}
#endif /* TARGET_WINDOWS */

/* IPC */
VOID
write_to_pipe(VOID *buffer, size_t count)
{
#ifdef TARGET_LINUX
    ssize_t bytes_written = 0;
    while(count > 0)
    {
        bytes_written = write(pipeHandle, buffer, count);
        if(bytes_written < 0)
        {
            perror("write");
            exit(1);
        }
        else
        {
            count -= bytes_written;
        }
    }
#elif TARGET_WINDOWS
    {
        using namespace WIN32_API;
        DWORD NumberOfBytesWritten;
        NumberOfBytesWritten = 0;
        WriteFile(pipeHandle, buffer, count, &NumberOfBytesWritten, NULL);
        if(NumberOfBytesWritten != count)
        {
            LOG("WriteFile failed ?\n");
        }
    }
#else
#error "This operating system is not supported."
#endif
}

#ifdef TARGET_LINUX
int
get_pipe_max_size()
{
    FILE *fp;
    int pipe_max_size = 0;

    fp = fopen("/proc/sys/fs/pipe-max-size", "r");
    if(fp == NULL)
        return 0;

    if(fscanf(fp, "%u", &pipe_max_size) != 1)
    {
        pipe_max_size = 0;
        
        fprintf(stderr, "Unable to read /proc/sys/fs/pipe-max-size properly\n");
    }

    return pipe_max_size;
}
#endif /* TARGET_LINUX */

char *fix_pipe_name(const char *name)
{
    char *p;
    if(name[0] == '\\' && name[1] == '\\') {
        p = (char *)name;
    } else {
        p = (char *)malloc(strlen(name) + 0x20);
        sprintf(p, "\\\\.\\pipe\\%s", name);
    }
    return p;
}

int
init_fifo(const char *fifoname)
{
#ifdef TARGET_LINUX
    int pipe_max_size;
    pipe_max_size = get_pipe_max_size();
    LOG("init_fifo");
    if(!pipe_max_size)
        return 0;

    LOG("opening handle");
    if((pipeHandle = open(fifoname, O_WRONLY)) < 0) {
        perror("open");
        return 0;
    }

    if(fcntl(pipeHandle, F_SETPIPE_SZ, pipe_max_size) < 0) {
        perror("fcntl");
        return 0;
    }

    return pipe_max_size;
#elif TARGET_WINDOWS
    {   
    using namespace WIN32_API;
    #define WINDOWS_PIPE_SIZE 0x8000
    char *pipename = fix_pipe_name(fifoname);
    LOG(pipename);
    pipeHandle = CreateNamedPipe(pipename,
        PIPE_ACCESS_OUTBOUND,
        PIPE_TYPE_BYTE | PIPE_WAIT,
        1,
        WINDOWS_PIPE_SIZE,
        WINDOWS_PIPE_SIZE,
        0,
        NULL);

    if(pipeHandle == INVALID_HANDLE_VALUE) {
        LOG("CreateNamedPipeA failed.\n");
        return 0;
    }

    if(!ConnectNamedPipe(pipeHandle, NULL)) {
        if(GetLastError() != ERROR_PIPE_CONNECTED) {
            LOG("ConnectNamedPipe failed.\n");
            return 0;
        }
    }
    return WINDOWS_PIPE_SIZE;
    }
#else
#error "This option is not supported yet."
#endif
}

void
write_header()
{
    uint8_t image_count;
    uint8_t *header;
    unsigned int header_size, pos;

    image_count = (uint8_t)whitelist.len;
    header_size = 1;
    header = NULL;

    for(uint8_t i = 0; i < image_count; i++)
        header_size += strlen(whitelist.list[i].path) + 2;

    header = (uint8_t*)malloc(header_size);
    *header = image_count;
    pos = 1; 

    for(uint8_t i = 0; i < image_count; i++)
    {
        *(uint16_t *)(header + pos) = (uint16_t)strlen(whitelist.list[i].path);
        pos += 2;
        memcpy(header + pos, whitelist.list[i].path, strlen(whitelist.list[i].path));
        pos += strlen(whitelist.list[i].path);
    }

    //[header] [number of images - 2 bytes][imagename - no-null byte]
    write_to_pipe(header, header_size);
}

/*
 * Main and usage
 */
KNOB<std::string> 
knob_database(
        KNOB_MODE_WRITEONCE, 
        "pintool",
        "o", "", 
        "specify an output file that will be generated from the target executable"
        );

KNOB<std::string>
knob_event(
    KNOB_MODE_WRITEONCE,
    "pintool",
    "e", "",
    "windows only - the name of event");

KNOB<std::string> 
knob_whitelist(
        KNOB_MODE_APPEND, 
        "pintool",
        "wht", "",
        "list of image names to instrument"
        );

void
pin_finish(INT32 code, VOID *v)
{
    char buffer[100];
    snprintf(buffer, 99, "pin_finish, bbls hit: %lu\n", bbls_count);
    LOG(buffer);
    write_to_pipe(bucket->start, (bucket->curr - bucket->start) * sizeof(node_t));
#ifdef TARGET_LINUX
    LOG("closing fifo");
    close(pipeHandle);
#elif TARGET_WINDOWS
    CloseHandle(pipeHandle);
    CloseHandle(TimeoutEvent);
#else
#error "This system is not supported."
#endif
}

INT32
usage()
{
    printf("This tool traces all the basic blocks "
            "and routines that are accessed during execution\n");
    return -1;
}

int
main(int argc, char **argv) {
    int pipe_size;

    if(PIN_Init(argc, argv)) {
        LOG("PIN_Init() failed.\n");
        return usage();
    }

    pipe_size = init_fifo(knob_database.Value().c_str());

    if(!pipe_size) {
        LOG("init_fifo() failed\n");
        fprintf(stderr, "Unable to make a fifo.\n");
        return -1;
    }
    LOG("pipe ok\n");

#ifdef TARGET_WINDOWS
    if(!knob_event.Value().size()) {
        LOG("Error in arguments (event was not set).\n");
        return usage();
    }

    /* On Windows, the instrumentation timeout is specified by an event object */
    {
        using namespace WIN32_API;

        TimeoutEvent = CreateEventA(NULL, TRUE, FALSE, knob_event.Value().c_str());

        if(TimeoutEvent == NULL) {
            LOG("CreateEventA failed.\n");
            fprintf(stderr, "CreateEventA failed %d.", GetLastError());
            return -2;
        }

        LOG("event ok\n");
    }
#endif /* TARGET_WINDOWS */


    bucket = init_bucket(pipe_size);
    LOG("bucket ok\n");
    wht_init(&knob_whitelist);
    LOG("whitelist ok\n");

    write_header();
    LOG("write_header ok\n");

    IMG_AddInstrumentFunction(img_load, NULL);
    IMG_AddUnloadFunction(img_unload, NULL);

#ifdef TARGET_WINDOWS
    /* 
     * In Windows in order to signal to the pintool that the instrumentation
     * should stop we're using an event object. A new thread is created to
     * watch is the event was set. On the other hand, on Linux, a SIGUSR2
     * signal is sent to the process.
     */
    PinThreadLock = (PIN_LOCK *)malloc(sizeof(PIN_LOCK));
    PIN_InitLock(PinThreadLock);
    if(PinThreadLock == NULL) {
        LOG("PIN_InitLock failed.\n");
        return usage();
    }
    THREADID tid;
    tid = PIN_SpawnInternalThread(CheckTerminationEvent, NULL, 0, &InternalPINThreadUid);
    if(tid == INVALID_THREADID) {
        LOG("PIN_SpawnInternalThread failed.\n");
        return -2;
    }
    PIN_AddPrepareForFiniFunction(TerminateInternalPINThreads, NULL);
#endif /* TARGET_WINDOWS */

    PIN_AddContextChangeFunction(context_change_cb, 0);

    TRACE_AddInstrumentFunction(trace_callback, NULL);

    // cleanup code
    PIN_AddFiniFunction(pin_finish, NULL);

    // never returns
    PIN_StartProgram();

    return 0;
}
