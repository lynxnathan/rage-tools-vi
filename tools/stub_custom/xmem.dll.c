/* XMem: the console memory allocator, expressed with VirtualAlloc.
 *
 * Signatures are inferred from call sites: the first call in this image is
 * XMemVirtualAlloc(0, 0x600000000, 0x20402000, 0x21), a 24 GiB reservation. Reserve and
 * commit succeed sparsely on 64-bit Windows, so the address space is not the limit.
 */
#include <windows.h>
#include <stdio.h>

/* The console reserves much more than it touches: this image asks for 24 GiB before it
 * creates a device. Committing that much fails, and Wine then relocates the request, which
 * breaks the title's GPU address arithmetic. Reserve only above 1 GiB and commit on touch, so
 * the reservation keeps the address the title asked for and stays sparse like the console's. */
#define COMMIT_ON_TOUCH_LIMIT (1024ull * 1024 * 1024)

/* Ranges we reserved but did not commit. The touch handler must only commit inside them:
 * intercepting every access violation (including the CRT heap's guard-page probes) breaks the
 * heap's own growth and turns every later allocation into NULL. */
#define TRACKED_RANGES 32
static struct { uintptr_t begin, end; } g_ranges[TRACKED_RANGES];
static volatile LONG g_range_count;

static void track(void *base, size_t size, int reserved_only)
{
    LONG index;
    if (!reserved_only || base == NULL || size == 0)
        return;
    index = InterlockedIncrement(&g_range_count) - 1;
    if (index < TRACKED_RANGES)
    {
        g_ranges[index].begin = (uintptr_t)base;
        g_ranges[index].end = (uintptr_t)base + size;
    }
}

static void *reserve(void *address, size_t size)
{
    DWORD flags = MEM_RESERVE | MEM_COMMIT;
    void *p;
    {
        /* Experiment knob: cap what is actually reserved, to see whether the title's own
         * allocator fails because the address space is already taken by these reservations. */
        const char *cap = getenv("STUB_XMEM_CAP");
        if (cap != NULL)
        {
            unsigned long long limit = strtoull(cap, NULL, 0);
            if (limit != 0 && size > (size_t)limit)
                size = (size_t)limit;
        }
    }
    if (size > COMMIT_ON_TOUCH_LIMIT)
        flags = MEM_RESERVE;
    /* A console allocation is page-granular and the title writes bookkeeping headers just past
     * the blocks it carves, so round up and keep a spare page at the end: with an exact-size
     * mapping the "block after" header lands in unmapped space (measured at image+0x69fe5). */
    size = (size + 0xffff) & ~(size_t)0xffff;
    size += 0x10000;
    p = VirtualAlloc(address, size, flags, PAGE_READWRITE);
    if (!p && address)
        p = VirtualAlloc(NULL, size, flags, PAGE_READWRITE);
    track(p, size, flags == MEM_RESERVE);
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!alloc(%p, %llx, %s) -> %p\n", GetCurrentThreadId(), address,
                (unsigned long long)size, flags == MEM_RESERVE ? "reserve" : "commit", p);
    return p;
}

/* Committing on touch: the title writes anywhere in a reservation and expects memory. */
/* Report the engine's failing allocation, read out of the exception context: the fault at
 * image+0x554bdcb is a write through a NULL result, and the size asked for is the number that
 * says whether the allocator refused a sane request or a corrupt one. */
static void report_failed_allocation(EXCEPTION_POINTERS *info)
{
    static int reported;
    HMODULE image = GetModuleHandleA(NULL);
    uintptr_t rip = (uintptr_t)info->ContextRecord->Rip;
    uintptr_t base = (uintptr_t)image;
    if (reported >= 3 || base == 0)
        return;
    if (rip != base + 0x554bdcb && rip != base + 0x69fe5)
        return;
    reported++;
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem! fault at %llx: rax=%p rbx=%llx rcx=%llx rdx=%llx r14=%llx rip=%llx\n",
                GetCurrentThreadId(), (unsigned long long)rip,
                (void *)info->ContextRecord->Rax,
                (unsigned long long)info->ContextRecord->Rbx,
                (unsigned long long)info->ContextRecord->Rcx,
                (unsigned long long)info->ContextRecord->Rdx,
                (unsigned long long)info->ContextRecord->R14,
                (unsigned long long)rip);
}

/* An access violation whose faulting address is in the title's heap but whose instruction is
 * outside the image is the CRT or a system DLL touching that memory; the engine's own frames are
 * the interesting part, so they are captured here. */
static void report_foreign_fault(EXCEPTION_POINTERS *info)
{
    static int reported;
    void *frames[16];
    HMODULE image = GetModuleHandleA(NULL);
    uintptr_t base = (uintptr_t)image;
    uintptr_t rip = (uintptr_t)info->ContextRecord->Rip;
    uintptr_t fault = (uintptr_t)info->ExceptionRecord->ExceptionInformation[1];
    USHORT captured, index;
    if (reported >= 2 || base == 0 || fault < 0x1000000 || fault >= 0x80000000ull)
        return;
    if (rip >= base && rip < base + 0x72a0000ull)
        return;
    reported++;
    {
        MEMORY_BASIC_INFORMATION page;
        void *page_address = (void *)(fault & ~(uintptr_t)0xfff);
        if (VirtualQuery(page_address, &page, sizeof(page)) != 0)
            fprintf(stderr, "[%lx] xmem! foreign page %p state=%lx protect=%lx region=%p/%llx\n",
                    GetCurrentThreadId(), page_address, (unsigned long)page.State,
                    (unsigned long)page.Protect, page.BaseAddress,
                    (unsigned long long)page.RegionSize);
        else
            fprintf(stderr, "[%lx] xmem! foreign page %p could not be queried\n",
                    GetCurrentThreadId(), page_address);
    }
    captured = RtlCaptureStackBackTrace(1, 16, frames, NULL);
    fprintf(stderr, "[%lx] xmem! foreign fault: rip=%llx fault=%llx frames:",
            GetCurrentThreadId(), (unsigned long long)rip, (unsigned long long)fault);
    for (index = 0; index < captured; index++)
        fprintf(stderr, " %llx", (unsigned long long)(uintptr_t)frames[index]);
    fprintf(stderr, "\n");
}

static LONG WINAPI commit_on_touch(EXCEPTION_POINTERS *info)
{
    void *fault = (void *)info->ExceptionRecord->ExceptionInformation[1];
    report_failed_allocation(info);
    report_foreign_fault(info);
    void *page = (void *)((uintptr_t)fault & ~(uintptr_t)0xfff);
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || fault == NULL)
    {
        if (getenv("STUB_TRACE"))
            fprintf(stderr, "[%lx] xmem! touch: not an access violation (%lx)\n",
                    GetCurrentThreadId(), (unsigned long)info->ExceptionRecord->ExceptionCode);
        return EXCEPTION_CONTINUE_SEARCH;
    }
    {
        LONG index;
        int inside = 0;
        MEMORY_BASIC_INFORMATION info;
        for (index = 0; index < g_range_count && index < TRACKED_RANGES; index++)
            if ((uintptr_t)fault >= g_ranges[index].begin &&
                (uintptr_t)fault < g_ranges[index].end)
                inside = 1;
        /* A console heap hands out virtual space and expects a write to commit it, wherever the
         * space came from. Asking the system whether the faulting page is merely reserved covers
         * ranges that arrived by another route (the title's own XMemAlloc wrappers included). */
        if (!inside && VirtualQuery(page, &info, sizeof(info)) != 0 &&
            info.State == MEM_RESERVE)
            inside = 1;
        /* The title's heap lives below 4 GiB and writes into space it reserved through a route
         * this stub does not see; committing a low faulting page is the console's behaviour
         * (virtual space there is always backed). STUB_TOUCH_LOW=0 turns it off. */
        if (!inside && (uintptr_t)fault < 0x100000000ull)
        {
            const char *enable = getenv("STUB_TOUCH_LOW");
            if (enable == NULL || strcmp(enable, "0") != 0)
                inside = 1;
        }
        if (inside && getenv("STUB_TRACE"))
            fprintf(stderr, "[%lx] xmem! touch: address %llx is inside\n",
                    GetCurrentThreadId(), (unsigned long long)(uintptr_t)fault);
        if (!inside)
            return EXCEPTION_CONTINUE_SEARCH;
    }
    {
        /* Commit a megabyte at a time: the title walks these ranges sparsely and one page per
         * fault turns into thousands of exceptions. */
        void *committed = VirtualAlloc(page, 16u << 20, MEM_COMMIT, PAGE_READWRITE);
        if (committed == NULL)
            committed = VirtualAlloc(page, 0x1000, MEM_COMMIT, PAGE_READWRITE);
        if (getenv("STUB_TRACE"))
            fprintf(stderr, "[%lx] xmem! commit on touch %p -> %p (ranges %ld)\n",
                    GetCurrentThreadId(), page, committed, (long)g_range_count);
        if (committed == NULL)
            return EXCEPTION_CONTINUE_SEARCH;
    }
    return EXCEPTION_CONTINUE_EXECUTION;
}

static void install_touch_handler(void)
{
    static int installed;
    if (installed)
        return;
    AddVectoredExceptionHandler(1, commit_on_touch);
    installed = 1;
}

void *XMemVirtualAlloc(void *address, size_t size, unsigned long long a, unsigned long long b)
{
    (void)a; (void)b;
    install_touch_handler();
    return reserve(address, size);
}

void *XMemAlloc(size_t size, unsigned long long alignment, unsigned long long flags)
{
    (void)alignment; (void)flags;
    return reserve(NULL, size);
}

void *XMemAllocDefault(size_t size, unsigned long long alignment)
{
    (void)alignment;
    return reserve(NULL, size);
}

/* Frees are not returned to the system: the title hands back sub-blocks of its own large
 * reservations, and releasing the containing range frees memory the title still writes to
 * (measured: a fault at image+0x69fe5 inside a range that had been released). Keeping the
 * placeholders alive is what a console does for the life of the process. */
unsigned long long XMemFree(void *p, size_t size, unsigned long long type)
{
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!free(%p, %llx, %llx) kept mapped\n", GetCurrentThreadId(),
                p, (unsigned long long)size, type);
    return 0;
}

unsigned long long XMemVirtualFree(void *p, size_t size, unsigned long long type)
{
    return XMemFree(p, size, type);
}

void XMemFreeDefault(void *p) { (void)XMemFree(p, 0, 0); }

/* "Tools memory" is the dev-kit scratch pool. Reporting it present is the shape a
 * development console reports; the image asking for it suggests a capability check. */
unsigned long long XMemIsToolsMemAvailable(void) { return 1; }

/* A Series X reports 16 GiB of GDDR6 with about 13.5 GiB usable by a title. The layout of this
 * structure is not public, so every 64-bit word is filled with a plausible figure and the call is
 * logged: if the title sizes a heap from it, zeros are worse than a real console's numbers. */
unsigned long long XMemGetWorkingSetStatistics(void *out, unsigned long long size)
{
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!XMemGetWorkingSetStatistics(%p, %llx)\n",
                GetCurrentThreadId(), out, size);
    if (out && size)
    {
        unsigned long long *words = (unsigned long long *)out;
        unsigned long long index;
        static const unsigned long long values[] = {
            16ull * 1024 * 1024 * 1024,   /* total */
            13ull * 1024 * 1024 * 1024,   /* free */
            3ull * 1024 * 1024 * 1024,    /* reserved */
            0, 0, 0, 0, 0
        };
        for (index = 0; index < size / sizeof(unsigned long long); index++)
            words[index] = index < sizeof(values) / sizeof(values[0]) ? values[index] : 0;
    }
    return 0;
}

/* Called with (address, size, ...) and checked for a truthy result: the image asserts
 * (image+0x5eb27be) when it comes back false. Back it with a real reservation so the caller's
 * expectation holds, and report the arguments that were passed. */
/* One argument only: the call site at image+0x221648e loads a single value into ecx (0x180
 * there, 0x280 elsewhere) and asserts unless the result is 1. On a console this hands the title
 * physical pages the GPU can map; here backing is the pool this stub already provides, so the
 * answer is "granted" and the value is logged for the record. */
unsigned long long XMemAllocatePhysicalPages(unsigned long long count)
{
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!XMemAllocatePhysicalPages(%llx) -> 1\n",
                GetCurrentThreadId(), count);
    return 1;
}
unsigned long long XMemFreePhysicalPages(void) { return 0; }
/* One argument, from the call site at image+0x2216a1d: the code passes a single value in rcx
 * and stores the result into a pointer slot. On a console this maps granted physical pages into
 * the caller's address space; here it hands back a fresh mapping of the same kind the allocator
 * uses, so the caller has something real to write through. */
unsigned long long XMemMapPhysicalPages(unsigned long long descriptor)
{
    void *p = reserve(NULL, 0x10000);
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!XMemMapPhysicalPages(%llx) -> %p\n", GetCurrentThreadId(),
                descriptor, p);
    return (unsigned long long)(uintptr_t)p;
}
unsigned long long XMemMapPhysicalPagesScatter(void) { return 0; }
unsigned long long XMemTransferMemory(void) { return 0; }
