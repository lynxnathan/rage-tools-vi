/* GameInput: the image imports ordinal 1 only, and calls it as `GameInputCreate(out)`.
 * FUN_1459258a0 caches the result and uses vtable slot +0x10 on it. The object answers
 * every slot with a zero return so the caller can continue.
 */
#include <windows.h>
#include <stdio.h>

static unsigned long long generic(void)
{
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] %s!method caller=%p\n", GetCurrentThreadId(),
                "gameinput", __builtin_return_address(0));
    return 0;
}
static void *vtable[512];
static void *object[1];

long long ord_1(void **out, unsigned long long flags)
{
    unsigned i;
    if (!object[0]) {
        for (i = 0; i < sizeof(vtable) / sizeof(vtable[0]); i++)
            vtable[i] = (void *)generic;
        object[0] = vtable;
    }
    if (getenv("STUB_TRACE"))
        fprintf(stderr, "[%lx] gameinput!ord_1(out=%p, flags=%llx)\n", (void *)out, flags);
    if (out) *out = object;
    return 0;
}
