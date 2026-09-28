#include "trainingdata/game_v6.h"

#include <bit>
#include <cmath>
#include <cstring>

#ifdef HAVE_LZMA
#include <lzma.h>
#endif

namespace lczero {

static_assert(std::endian::native == std::endian::little,
              "the v6 container is little-endian, like the 45940-byte records");

namespace {

constexpr int kPly = 27;
constexpr int kPlies = 8;
constexpr int kFloats = 11;  // result_q/d, root_q/d, best_q/d, played_q/d, orig_q/d, policy_kld

uint32_t Bits(float f) {
  uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}
const uint32_t kMinusOneBits = Bits(-1.0f);

template <typename T>
void Append(std::string* s, const std::vector<T>& v) {
  s->append(reinterpret_cast<const char*>(v.data()), v.size() * sizeof(T));
}

// Integer visit counts n with float(n) / float(sum n) == pi bit for bit (the
// engine's own formula, training_extract.cc), or false. The engine's total is
// the sum of the root's edge visits, normally `visits` - 1 (the root's own
// visit); a few neighbours are tried too. Same rule as trainingdata_v6.py.
bool PolicyCounts(const float* pi, const uint16_t* idx, size_t n, uint32_t visits,
                  std::vector<uint16_t>* out) {
  out->resize(n);
  if (n == 0) return true;
  const int64_t v = visits;
  for (int64_t t : {v - 1, v, v - 2, v + 1}) {
    if (t < 0 || t > int64_t{0xFFFF} * static_cast<int64_t>(n)) continue;
    int64_t sum = 0;
    bool ok = true;
    for (size_t i = 0; i < n && ok; ++i) {
      const double c = std::nearbyint(static_cast<double>(pi[idx[i]]) * static_cast<double>(t));
      if (!(c >= 0.0 && c <= 65535.0)) { ok = false; break; }
      (*out)[i] = static_cast<uint16_t>(c);
      sum += (*out)[i];
    }
    if (!ok || sum != t) continue;
    for (size_t i = 0; i < n && ok; ++i) {
      const float back = t == 0 ? 0.0f
                                : static_cast<float>((*out)[i]) / static_cast<float>(t);
      ok = Bits(back) == Bits(pi[idx[i]]);
    }
    if (ok) return true;
  }
  return false;
}

}  // namespace

void OtherFrame(const uint64_t in[27][2], uint64_t out[27][2]) {
  auto mirror = [](const uint64_t w[2], uint64_t o[2]) {
    const unsigned __int128 v = (static_cast<unsigned __int128>(w[1]) << 64) | w[0];
    unsigned __int128 m = 0;
    for (int r = 0; r < 10; ++r) m |= ((v >> (12 * r)) & 0xFFF) << (12 * (9 - r));
    o[0] = static_cast<uint64_t>(m);
    o[1] = static_cast<uint64_t>(m >> 64);
  };
  for (int p = 0; p < 13; ++p) {
    mirror(in[p + 13], out[p]);
    mirror(in[p], out[p + 13]);
  }
  out[26][0] = in[26][0];
  out[26][1] = in[26][1];
}

bool GameV6Encoder::Add(const TrainingDataV1& r) {
  if (flags_.empty()) {
    version_ = r.version;
    input_format_ = r.input_format;
  } else if (r.version != version_ || r.input_format != input_format_) {
    return false;
  }
  uint8_t flags = 0;

  // --- Policy: the legal slots (>= 0) if every other slot is exactly -1.
  float pi[kPolicySize];
  std::memcpy(pi, r.probabilities, sizeof(pi));
  thread_local std::vector<uint16_t> legal, counts;
  legal.clear();
  bool well_formed = true;
  for (int i = 0; i < kPolicySize; ++i) {
    if (pi[i] >= 0.0f) {
      legal.push_back(static_cast<uint16_t>(i));
    } else if (Bits(pi[i]) != kMinusOneBits) {  // NaN or another negative value
      well_formed = false;
      break;
    }
  }
  if (!well_formed) {
    flags |= kGameV6FlagDensePi;
    n_legal_.push_back(0);
    pi_dense_.insert(pi_dense_.end(), pi, pi + kPolicySize);
  } else {
    n_legal_.push_back(static_cast<uint16_t>(legal.size()));
    uint16_t prev = 0;
    for (uint16_t i : legal) {
      delta_.push_back(static_cast<uint16_t>(i - prev));
      prev = i;
    }
    if (PolicyCounts(pi, legal.data(), legal.size(), r.visits, &counts)) {
      counts_.insert(counts_.end(), counts.begin(), counts.end());
    } else {
      flags |= kGameV6FlagFloatPi;
      for (uint16_t i : legal) pi_float_.push_back(pi[i]);
    }
  }

  // --- Planes: ply 0 always; plies 1..7 only when they do not chain.
  uint64_t planes[kPlies][kPly][2];
  std::memcpy(planes, r.piece_planes, sizeof(planes));
  cur_.insert(cur_.end(), &planes[0][0][0], &planes[0][0][0] + kPly * 2);
  if (!have_prev_ || std::memcmp(planes[1], expect_, sizeof(expect_)) != 0) {
    flags |= kGameV6FlagFull;
    hist_.insert(hist_.end(), &planes[1][0][0], &planes[1][0][0] + 7 * kPly * 2);
  }
  for (int d = 0; d < 7; ++d) OtherFrame(planes[d], expect_[d]);
  have_prev_ = true;

  // --- Scalars, column by column.
  rule50_.push_back(r.rule50_count);
  castling_[0].push_back(r.castling_us_ooo_sq);
  castling_[1].push_back(r.castling_us_oo_sq);
  castling_[2].push_back(r.castling_them_ooo_sq);
  castling_[3].push_back(r.castling_them_oo_sq);
  uint64_t ep[2];
  std::memcpy(ep, r.ep_mask, sizeof(ep));
  ep_.push_back(ep[0]);
  ep_.push_back(ep[1]);
  checks_us_.push_back(r.checks_remaining_us);
  checks_them_.push_back(r.checks_remaining_them);
  stm_.push_back(r.side_to_move);
  float f[kFloats];
  std::memcpy(f, &r.result_q, sizeof(f));  // the 11 floats are contiguous in the record
  for (int i = 0; i < kFloats; ++i) floats_[i].push_back(f[i]);
  visits_.push_back(r.visits);
  played_idx_.push_back(r.played_idx);
  best_idx_.push_back(r.best_idx);
  flags_.push_back(flags);
  return true;
}

std::string GameV6Encoder::Payload() const {
  std::string s;
  const uint32_t n = static_cast<uint32_t>(flags_.size());
  uint32_t l_total = 0, f = 0;
  for (uint16_t k : n_legal_) l_total += k;
  for (uint8_t k : flags_) f += (k & kGameV6FlagFull) ? 1 : 0;
  const uint32_t head[7] = {kGameV6Revision, version_, input_format_, n, l_total,
                            static_cast<uint32_t>(pi_float_.size()), f};
  s.append(kGameV6Magic, 4);
  s.append(reinterpret_cast<const char*>(head), sizeof(head));
  Append(&s, flags_);
  Append(&s, n_legal_);
  Append(&s, delta_);
  Append(&s, counts_);
  Append(&s, pi_float_);
  Append(&s, pi_dense_);
  Append(&s, cur_);
  Append(&s, hist_);
  Append(&s, rule50_);
  for (const auto& c : castling_) Append(&s, c);
  Append(&s, ep_);
  Append(&s, checks_us_);
  Append(&s, checks_them_);
  Append(&s, stm_);
  for (const auto& c : floats_) Append(&s, c);
  Append(&s, visits_);
  Append(&s, played_idx_);
  Append(&s, best_idx_);
  return s;
}

bool DecodeGameV6Payload(const std::string& payload, std::vector<TrainingDataV1>* out,
                         std::string* err) {
  out->clear();
  size_t pos = 0;
  auto fail = [&](const char* why) {
    if (err) *err = why;
    out->clear();
    return false;
  };
  // Reserve `count` elements of type T at the cursor; nullptr if past the end.
  auto take = [&](size_t count, size_t size) -> const char* {
    if (count > (payload.size() - pos) / size) return nullptr;
    const char* p = payload.data() + pos;
    pos += count * size;
    return p;
  };
  if (payload.size() < 32 || std::memcmp(payload.data(), kGameV6Magic, 4) != 0)
    return fail("not a v6 game (magic)");
  uint32_t head[7];
  std::memcpy(head, payload.data() + 4, sizeof(head));
  pos = 32;
  const uint32_t rev = head[0], version = head[1], input_format = head[2], n = head[3],
                 l_total = head[4], lf = head[5], f = head[6];
  if (rev != kGameV6Revision) return fail("unknown v6 container revision");

  const char* flags = take(n, 1);
  const char* n_legal_p = take(n, 2);
  if (!flags || !n_legal_p) return fail("truncated v6 game");
  std::vector<uint16_t> n_legal(n);
  std::memcpy(n_legal.data(), n_legal_p, n * 2u);
  uint64_t sum_legal = 0, sum_float = 0;
  uint32_t n_full = 0, n_dense = 0;
  for (uint32_t k = 0; k < n; ++k) {
    const uint8_t fl = static_cast<uint8_t>(flags[k]);
    if (fl & ~(kGameV6FlagFull | kGameV6FlagFloatPi | kGameV6FlagDensePi))
      return fail("invalid v6 flags");
    if ((fl & kGameV6FlagDensePi) && ((fl & kGameV6FlagFloatPi) || n_legal[k] != 0))
      return fail("invalid v6 flags");
    sum_legal += n_legal[k];
    if (fl & kGameV6FlagFloatPi) sum_float += n_legal[k];
    n_full += (fl & kGameV6FlagFull) ? 1 : 0;
    n_dense += (fl & kGameV6FlagDensePi) ? 1 : 0;
  }
  if (n > 0 && !(static_cast<uint8_t>(flags[0]) & kGameV6FlagFull))
    return fail("invalid v6 flags (first record not full)");
  if (sum_legal != l_total || sum_float != lf || n_full != f)
    return fail("inconsistent v6 header");

  const char* delta = take(l_total, 2);
  const char* counts = take(l_total - lf, 2);
  const char* pif = take(lf, 4);
  const char* pid = take(static_cast<size_t>(n_dense) * kPolicySize, 4);
  const char* cur = take(static_cast<size_t>(n) * kPly * 2, 8);
  const char* hist = take(static_cast<size_t>(f) * 7 * kPly * 2, 8);
  const char* rule50 = take(n, 1);
  const char* castling = take(4u * n, 1);
  const char* ep = take(2u * n, 8);
  const char* checks_us = take(n, 1);
  const char* checks_them = take(n, 1);
  const char* stm = take(n, 1);
  const char* floats = take(static_cast<size_t>(kFloats) * n, 4);
  const char* visits = take(n, 4);
  const char* played = take(n, 2);
  const char* best = take(n, 2);
  if (!delta || !counts || !pif || !pid || !cur || !hist || !rule50 || !castling || !ep ||
      !checks_us || !checks_them || !stm || !floats || !visits || !played || !best)
    return fail("truncated v6 game");
  if (pos != payload.size()) return fail("v6 game has trailing bytes");

  out->resize(n);
  size_t li = 0, ci = 0, fi = 0, di = 0, hi = 0;
  for (uint32_t k = 0; k < n; ++k) {
    TrainingDataV1& r = (*out)[k];
    const uint8_t fl = static_cast<uint8_t>(flags[k]);
    r.version = version;
    r.input_format = input_format;

    // Policy.
    if (fl & kGameV6FlagDensePi) {
      std::memcpy(r.probabilities, pid + di * kPolicySize * 4, kPolicySize * 4);
      ++di;
    } else {
      float pi[kPolicySize];
      std::fill_n(pi, kPolicySize, -1.0f);
      const size_t m = n_legal[k];
      uint64_t total = 0;
      if (!(fl & kGameV6FlagFloatPi)) {
        for (size_t i = 0; i < m; ++i) {
          uint16_t c;
          std::memcpy(&c, counts + (ci + i) * 2, 2);
          total += c;
        }
      }
      uint32_t idx = 0;
      for (size_t i = 0; i < m; ++i, ++li) {
        uint16_t d;
        std::memcpy(&d, delta + li * 2, 2);
        if (i > 0 && d == 0) return fail("invalid v6 legal-move indices");
        idx += d;
        if (idx >= static_cast<uint32_t>(kPolicySize)) return fail("invalid v6 legal-move indices");
        if (fl & kGameV6FlagFloatPi) {
          std::memcpy(&pi[idx], pif + fi * 4, 4);
          ++fi;
        } else {
          uint16_t c;
          std::memcpy(&c, counts + ci * 2, 2);
          ++ci;
          pi[idx] = total == 0 ? 0.0f : static_cast<float>(c) / static_cast<float>(total);
        }
      }
      std::memcpy(r.probabilities, pi, sizeof(pi));
    }

    // Planes.
    uint64_t planes[kPlies][kPly][2];
    std::memcpy(planes[0], cur + static_cast<size_t>(k) * kPly * 16, kPly * 16);
    if (fl & kGameV6FlagFull) {
      std::memcpy(planes[1], hist + hi * 7 * kPly * 16, 7 * kPly * 16);
      ++hi;
    } else {
      uint64_t prev[kPlies][kPly][2];
      std::memcpy(prev, (*out)[k - 1].piece_planes, sizeof(prev));
      for (int d = 1; d < kPlies; ++d) OtherFrame(prev[d - 1], planes[d]);
    }
    std::memcpy(r.piece_planes, planes, sizeof(planes));

    // Scalars.
    r.rule50_count = static_cast<uint8_t>(rule50[k]);
    r.castling_us_ooo_sq = static_cast<uint8_t>(castling[k]);
    r.castling_us_oo_sq = static_cast<uint8_t>(castling[n + k]);
    r.castling_them_ooo_sq = static_cast<uint8_t>(castling[2u * n + k]);
    r.castling_them_oo_sq = static_cast<uint8_t>(castling[3u * n + k]);
    std::memcpy(r.ep_mask, ep + static_cast<size_t>(k) * 16, 16);
    r.checks_remaining_us = static_cast<uint8_t>(checks_us[k]);
    r.checks_remaining_them = static_cast<uint8_t>(checks_them[k]);
    r.side_to_move = static_cast<uint8_t>(stm[k]);
    float fv[kFloats];
    for (int i = 0; i < kFloats; ++i)
      std::memcpy(&fv[i], floats + (static_cast<size_t>(i) * n + k) * 4, 4);
    std::memcpy(&r.result_q, fv, sizeof(fv));
    std::memcpy(&r.visits, visits + static_cast<size_t>(k) * 4, 4);
    std::memcpy(&r.played_idx, played + static_cast<size_t>(k) * 2, 2);
    std::memcpy(&r.best_idx, best + static_cast<size_t>(k) * 2, 2);
  }
  return true;
}

#ifdef HAVE_LZMA
bool XzCompress(const std::string& in, std::string* out) {
  lzma_options_lzma opt;
  if (lzma_lzma_preset(&opt, 9 | LZMA_PRESET_EXTREME)) return false;
  opt.dict_size = 1u << 20;  // one game; keeps the encoder at ~11 MB instead of ~674 MB
  lzma_filter filters[] = {{LZMA_FILTER_LZMA2, &opt}, {LZMA_VLI_UNKNOWN, nullptr}};
  out->resize(lzma_stream_buffer_bound(in.size()));
  size_t out_pos = 0;
  if (lzma_stream_buffer_encode(filters, LZMA_CHECK_CRC64, nullptr,
                                reinterpret_cast<const uint8_t*>(in.data()), in.size(),
                                reinterpret_cast<uint8_t*>(out->data()), &out_pos,
                                out->size()) != LZMA_OK)
    return false;
  out->resize(out_pos);
  return true;
}

bool XzDecompress(const std::string& in, std::string* out) {
  lzma_stream strm = LZMA_STREAM_INIT;
  if (lzma_stream_decoder(&strm, UINT64_MAX, 0) != LZMA_OK) return false;
  strm.next_in = reinterpret_cast<const uint8_t*>(in.data());
  strm.avail_in = in.size();
  out->clear();
  uint8_t buf[1 << 16];
  lzma_ret ret = LZMA_OK;
  while (ret == LZMA_OK) {
    strm.next_out = buf;
    strm.avail_out = sizeof(buf);
    ret = lzma_code(&strm, LZMA_FINISH);
    out->append(reinterpret_cast<const char*>(buf), sizeof(buf) - strm.avail_out);
  }
  const bool ok = ret == LZMA_STREAM_END && strm.avail_in == 0;
  lzma_end(&strm);
  return ok;
}
#else
bool XzCompress(const std::string&, std::string*) { return false; }
bool XzDecompress(const std::string&, std::string*) { return false; }
#endif

}  // namespace lczero
