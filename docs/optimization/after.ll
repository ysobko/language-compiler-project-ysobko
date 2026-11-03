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
define i32 @"main"()
{
entry:
  %"_inline_1_x" = alloca i32
  store i32 10, i32* %"_inline_1_x"
  %"_inline_1_x.value" = load i32, i32* %"_inline_1_x"
  %"arithmetic.checked" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"_inline_1_x.value", i32 2)
  %"arithmetic.result" = extractvalue {i32, i1} %"arithmetic.checked", 0
  %"arithmetic.overflow" = extractvalue {i32, i1} %"arithmetic.checked", 1
  br i1 %"arithmetic.overflow", label %"arithmetic.overflow.error", label %"arithmetic.continue"
arithmetic.overflow.error:
  call void @"abort"()
  unreachable
arithmetic.continue:
  %".6" = call i32 (i8*, ...) @"printf"(i8* getelementptr ([4 x i8], [4 x i8]* @"traffica_fmt_print_i32", i32 0, i32 0), i32 %"arithmetic.result")
  ret i32 0
}

declare {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %".1", i32 %".2")

declare void @"abort"()
