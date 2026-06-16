#pragma once

// Enable thread safety attributes only with clang.
#if defined(__clang__) && (!defined(SWIG))
#define ATTRIBUTE__(x) __attribute__((x))
#else
#define ATTRIBUTE__(x)  // no-op
#endif

#define CAPABILITY(x) ATTRIBUTE__(capability(x))
#define SCOPED_CAPABILITY ATTRIBUTE__(scoped_lockable)
#define GUARDED_BY(x) ATTRIBUTE__(guarded_by(x))
#define PT_GUARDED_BY(x) ATTRIBUTE__(pt_guarded_by(x))
#define ACQUIRED_BEFORE(...) ATTRIBUTE__(acquired_before(__VA_ARGS__))
#define ACQUIRED_AFTER(...) ATTRIBUTE__(acquired_after(__VA_ARGS__))
#define REQUIRES(...) ATTRIBUTE__(requires_capability(__VA_ARGS__))
#define REQUIRES_SHARED(...) \
  ATTRIBUTE__(requires_shared_capability(__VA_ARGS__))
#define ACQUIRE(...) ATTRIBUTE__(acquire_capability(__VA_ARGS__))
#define ACQUIRE_SHARED(...) ATTRIBUTE__(acquire_shared_capability(__VA_ARGS__))
#define RELEASE(...) ATTRIBUTE__(release_capability(__VA_ARGS__))
#define RELEASE_SHARED(...) ATTRIBUTE__(release_shared_capability(__VA_ARGS__))
#define TRY_ACQUIRE(...) ATTRIBUTE__(try_acquire_capability(__VA_ARGS__))
#define TRY_ACQUIRE_SHARED(...) \
  ATTRIBUTE__(try_acquire_shared_capability(__VA_ARGS__))
#define EXCLUDES(...) ATTRIBUTE__(locks_excluded(__VA_ARGS__))
#define ASSERT_CAPABILITY(x) ATTRIBUTE__(assert_capability(x))
#define ASSERT_SHARED_CAPABILITY(x) ATTRIBUTE__(assert_shared_capability(x))
#define RETURN_CAPABILITY(x) ATTRIBUTE__(lock_returned(x))
#define PACKED_STRUCT ATTRIBUTE__(packed)

#define NO_THREAD_SAFETY_ANALYSIS ATTRIBUTE__(no_thread_safety_analysis)
