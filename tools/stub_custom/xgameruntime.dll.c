/* XGameRuntime: the GDK API loader's implementation module.
 *
 * FUN_1455e2a70 loads "xgameruntime.dll" from the image directory and resolves
 * QueryApiImpl, InitializeApiImpl, InitializeApiImplEx, InitializeApiImplEx2,
 * XErrorReport and UninitializeApiImpl; without them it returns 0x89240101 and the CRT
 * aborts. FUN_1455ddff0 then queries an interface (first argument is the out-slot, the
 * second points into read-only image data) and calls vtable slots +0x10 and +0xe8, so the
 * slot must hold an object whose vtable answers every index.
 */
#include <windows.h>
#include <stdio.h>

#define TRACE(fmt, ...) do { if (getenv("STUB_TRACE")) \
    fprintf(stderr, "[%lx] xgameruntime!%s: " fmt "\n", GetCurrentThreadId(), __func__, __VA_ARGS__); } while (0)

static unsigned long long generic(void)
{
    return 0;
}

static void *vtable[512];
static void *object[1];

static void init_object(void)
{
    unsigned i;
    if (object[0]) return;
    for (i = 0; i < sizeof(vtable) / sizeof(vtable[0]); i++)
        vtable[i] = (void *)generic;
    object[0] = vtable;
}

/* Caller shape, from FUN_1455ddff0: the same GUID pointer arrives in the first two
 * registers and the writable out-slot is the third. */
long long QueryApiImpl(const void *iid_a, const void *iid_b, void **out, unsigned long long r9)
{
    init_object();
    TRACE("iid=%p iid2=%p out=%p r9=%llx", iid_a, iid_b, (void *)out, r9);
    if (out) *out = object;
    return 0;
}

long long InitializeApiImpl(void)
{
    TRACE("", 0);
    return 0;
}

long long InitializeApiImplEx(unsigned long long a, unsigned long long b)
{
    TRACE("a=%llx b=%llx", a, b);
    return 0;
}

long long InitializeApiImplEx2(unsigned long long a, unsigned long long b)
{
    TRACE("a=%llx b=%llx", a, b);
    return 0;
}

long long XErrorReport(unsigned long long code, unsigned long long a, unsigned long long b)
{
    TRACE("code=%llx a=%llx b=%llx", code, a, b);
    return 0;
}

long long UninitializeApiImpl(void)
{
    TRACE("", 0);
    return 0;
}
