#include <jni.h>
#include <string>

namespace {

constexpr const char* kEngineStatus =
    "Native engine bridge loaded; AI inference is not connected yet.";

}  // namespace

extern "C"
JNIEXPORT jstring JNICALL
Java_com_agentsimulation_engine_NativeInferenceBridge_nativeGetEngineStatus(
    JNIEnv* env,
    jobject /* thiz */) {

    return env->NewStringUTF(kEngineStatus);
}
