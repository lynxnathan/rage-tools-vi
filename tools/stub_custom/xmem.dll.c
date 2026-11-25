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

static LONG WINAPI commit_on_touch(EXCEPTION_POINTERS *info)
{
    void *fault = (void *)info->ExceptionRecord->ExceptionInformation[1];
    report_failed_allocation(info);
    void *page = (void *)((uintptr_t)fault & ~(uintptr_t)0xfff);
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_ACCESS_VIOLATION || fault == NULL)
        return EXCEPTION_CONTINUE_SEARCH;
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

unsigned long long XMemGetWorkingSetStatistics(void *out, unsigned long long size)
{
    if (out && size) memset(out, 0, (size_t)size);
    return 0;
}

/* Called with (address, size, ...) and checked for a truthy result: the image asserts
 * (image+0x5eb27be) when it comes back false. Back it with a real reservation so the caller's
 * expectation holds, and report the arguments that were passed. */
unsigned long long XMemAllocatePhysicalPages(unsigned long long address, unsigned long long size,
                                             unsigned long long a, unsigned long long b)
{
    void *p;
    (void)a; (void)b;
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] xmem!XMemAllocatePhysicalPages(%p, %llx, %llx, %llx)\n",
                GetCurrentThreadId(), (void *)(uintptr_t)address, size, a, b);
    p = reserve((void *)(uintptr_t)address, (size_t)size);
    return p != NULL ? 1 : 0;
}
unsigned long long XMemFreePhysicalPages(void) { return 0; }
unsigned long long XMemMapPhysicalPages(void) { return 0; }
unsigned long long XMemMapPhysicalPagesScatter(void) { return 0; }
unsigned long long XMemTransferMemory(void) { return 0; }
