target triple = "amdgcn-amd-amdhsa"

define amdgpu_kernel void @k(ptr addrspace(1) %in, ptr addrspace(1) %out) #0 {
  %i = load i32, ptr addrspace(1) %in
  %m = mul i32 %i, 7
  %a = add i32 %m, 3
  %s = shl i32 %a, 2
  %x = sitofp i32 %s to float
  %y = fmul float %x, 0x3FF8000000000000
  %z = fadd float %y, 1.500000e+00
  %r = fptosi float %z to i32
  store i32 %r, ptr addrspace(1) %out
  ret void
}
attributes #0 = { "amdgpu-flat-work-group-size"="1,256" }
