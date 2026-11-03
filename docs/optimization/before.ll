; ModuleID = "traffica"
target triple = "aarch64-unknown-linux-gnu"
target datalayout = ""

declare i32 @"scanf"(i8* %".1", ...)

@"traffica_fmt_int" = internal constant [3 x i8] c"%d\00"
declare i32 @"printf"(i8* %".1", ...)

@"traffica_fmt_print_i32" = internal constant [4 x i8] c"%d\0a\00"
@"traffica_fmt_print_i64" = internal constant [6 x i8] c"%lld\0a\00"
@"traffica_fmt_print_string" = internal constant [4 x i8] c"%s\0a\00"
@"traffica_fmt_raw_string" = internal constant [3 x i8] c"%s\00"
@"traffica_fmt_raw_i32" = internal constant [3 x i8] c"%d\00"
@"traffica_fmt_raw_i64" = internal constant [5 x i8] c"%lld\00"
@"traffica_bool_true" = internal constant [5 x i8] c"true\00"
@"traffica_bool_false" = internal constant [6 x i8] c"false\00"
define i32 @"traffica_double"(i32 %"x")
{
entry:
  %"x.addr" = alloca i32
  store i32 %"x", i32* %"x.addr"
  %"x.value" = load i32, i32* %"x.addr"
  %"arithmetic.checked" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"x.value", i32 2)
  %"arithmetic.result" = extractvalue {i32, i1} %"arithmetic.checked", 0
  %"arithmetic.overflow" = extractvalue {i32, i1} %"arithmetic.checked", 1
  br i1 %"arithmetic.overflow", label %"arithmetic.overflow.error", label %"arithmetic.continue"
arithmetic.overflow.error:
  call void @"abort"()
  unreachable
arithmetic.continue:
  ret i32 %"arithmetic.result"
}

declare {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %".1", i32 %".2")

declare void @"abort"()

define i32 @"main"()
{
entry:
  %"call.double" = call i32 @"traffica_double"(i32 10)
  %".2" = call i32 (i8*, ...) @"printf"(i8* getelementptr ([4 x i8], [4 x i8]* @"traffica_fmt_print_i32", i32 0, i32 0), i32 %"call.double")
  ret i32 0
}
