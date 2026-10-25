/* dataloader.js - loads the published data files and runs the recommendation engine in the student's own browser.
   Works in browsers (window.DataLoader) and Node (module.exports, used by the tests).
   Steps: manifest -> base file -> work out which seat types apply to the student -> fetch ONLY those cutoff files
   -> check each file's SHA-256 fingerprint -> hand everything to Recommender.recommend().
   If any file is missing or fails its check, loading stops with a clear error. A partial data set is never used. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DataLoader = factory();
})(this, function () {
  "use strict";

  function LoadError(code, message) { var e = new Error(message); e.code = code; e.name = "LoadError"; return e; }
  var BASE_TABLES = ["colleges", "branches", "seat_types", "vacancies", "fees", "accreditation", "placements", "hostels",
    "quality_indicators", "source_documents", "refresh_status", "data_version"];

  function expand(t) {
    var cols = t.columns;
    return t.rows.map(function (r) { var o = {}; for (var i = 0; i < cols.length; i++) o[cols[i]] = r[i]; return o; });
  }
  function hex(buf) {
    return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }
  function defaultVerify(bytes, expected) {
    var c = (typeof crypto !== "undefined" && crypto.subtle) ? crypto : null;
    if (!c) return Promise.resolve(true);               // very old browser or insecure page: skip the fingerprint check
    return c.subtle.digest("SHA-256", bytes).then(function (d) { return hex(d) === expected; });
  }

  function fetchBytes(url, opts) {
    var attempt = function (n) {
      return opts.fetchFn(url, opts.fetchOptions).then(function (res) {
        if (!res.ok) throw LoadError("NETWORK", "Could not load " + url + " (status " + res.status + ").");
        return res.arrayBuffer();
      }).catch(function (e) {
        if (n < 1) return attempt(n + 1);                // one retry for flaky mobile connections
        throw e.name === "LoadError" ? e : LoadError("NETWORK", "Could not load " + url + ". Please check your internet connection and try again.");
      });
    };
    return attempt(0);
  }
  function parse(bytes, url) {
    try { return JSON.parse(new TextDecoder("utf-8").decode(bytes)); }
    catch (e) { throw LoadError("BAD_FILE", "The data file " + url + " is damaged."); }
  }
  function getVerified(base, meta, opts, log) {
    var url = base + meta.file;
    return fetchBytes(url, opts).then(function (bytes) {
      return opts.verify(bytes, meta.sha256).then(function (ok) {
        if (!ok) throw LoadError("HASH_MISMATCH", "The data file " + meta.file + " did not match its fingerprint. Please reload the page.");
        log.files.push(meta.file); log.bytes += bytes.byteLength;
        return parse(bytes, url);
      });
    });
  }

  /** Loads everything needed for one student and returns {data, manifest, files, bytes}. */
  function loadForStudent(student, options) {
    var o = options || {};
    var R = o.Recommender || (typeof Recommender !== "undefined" ? Recommender : null);
    if (!R) return Promise.reject(LoadError("NO_ENGINE", "The recommendation engine is not loaded."));
    var opts = { fetchFn: o.fetchFn || function (u, init) { return fetch(u, init); }, verify: o.verify || defaultVerify, fetchOptions: undefined };
    var base = o.baseUrl || "data/", log = { files: [], bytes: 0 };
    opts.fetchOptions = { cache: "no-cache" };             // the manifest must always be fresh; data files have unique names
    return fetchBytes(base + "manifest.json", opts).then(function (mb) {
      var manifest = parse(mb, base + "manifest.json");
      if (!manifest || manifest.format !== 1 || !manifest.base || !manifest.cutoffs) throw LoadError("BAD_MANIFEST", "The data index is not in the expected format.");
      opts.fetchOptions = undefined;                       // normal caching for the uniquely named data files
      return getVerified(base, manifest.base, opts, log).then(function (baseTables) {
        var data = {};
        BASE_TABLES.forEach(function (t) { if (!baseTables[t]) throw LoadError("BAD_FILE", "The data file is missing the table " + t + "."); data[t] = expand(baseTables[t]); });
        var eligible = R.eligibleSeatTypes(student, data.seat_types, R.DEFAULTS).filter(function (c) { return manifest.cutoffs[c]; }).sort();
        data.historical_cutoffs = []; data.current_cutoffs = [];
        return Promise.all(eligible.map(function (code) { return getVerified(base, manifest.cutoffs[code], opts, log); })).then(function (shards) {
          shards.forEach(function (s) {
            data.historical_cutoffs = data.historical_cutoffs.concat(expand(s.historical_cutoffs));
            data.current_cutoffs = data.current_cutoffs.concat(expand(s.current_cutoffs));
          });
          return { data: data, manifest: manifest, files: log.files.slice(), bytes: log.bytes, seatTypesLoaded: eligible };
        });
      });
    });
  }

  /** Convenience: load the right files and run the engine. Resolves to the engine's answer plus file info. */
  function recommend(input, options) {
    var o = options || {};
    var R = o.Recommender || (typeof Recommender !== "undefined" ? Recommender : null);
    var student = { candidateType: input && input.candidateType, category: input && input.category, gender: (input && input.gender) || null };
    return loadForStudent(student, o).then(function (L) {
      var res = R.recommend(input, L.data, o.engineOptions);
      if (res && res.meta) { res.meta.dataFiles = L.files; res.meta.dataBytesDownloaded = L.bytes; res.meta.dataGeneratedAt = L.manifest.generated_at; }
      return res;
    });
  }

  return { loadForStudent: loadForStudent, recommend: recommend, expand: expand };
});
