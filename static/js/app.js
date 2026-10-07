document.addEventListener("DOMContentLoaded", function () {
  var generateBtn = document.getElementById("generate-btn");
  if (generateBtn) {
    var form = generateBtn.closest("form");
    form.addEventListener("submit", function () {
      if (form.checkValidity()) {
        generateBtn.disabled = true;
        generateBtn.textContent = "Generating estimate... (about 20s)";
      }
    });
  }

  var confirms = document.querySelectorAll("form[data-confirm]");
  confirms.forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });

  var VEHICLES = {
    "Acura": ["ILX", "Integra", "MDX", "RDX", "TLX", "TSX"],
    "Audi": ["A3", "A4", "A5", "A6", "Q3", "Q5", "Q7", "S4"],
    "BMW": ["2 Series", "3 Series", "5 Series", "7 Series", "X1", "X3", "X5"],
    "Buick": ["Enclave", "Encore", "Envision", "LaCrosse", "Regal"],
    "Cadillac": ["CT4", "CT5", "Escalade", "XT4", "XT5", "XT6"],
    "Chevrolet": ["Camaro", "Colorado", "Equinox", "Impala", "Malibu", "Silverado", "Suburban", "Tahoe", "Traverse", "Trax"],
    "Chrysler": ["300", "Pacifica", "Voyager"],
    "Dodge": ["Challenger", "Charger", "Durango", "Grand Caravan"],
    "Ford": ["Bronco", "EcoSport", "Edge", "Escape", "Explorer", "F-150", "Fusion", "Mustang", "Ranger", "Taurus"],
    "GMC": ["Acadia", "Sierra", "Terrain", "Yukon"],
    "Honda": ["Accord", "Civic", "CR-V", "HR-V", "Odyssey", "Passport", "Pilot", "Ridgeline"],
    "Hyundai": ["Accent", "Elantra", "Kona", "Palisade", "Santa Fe", "Sonata", "Tucson", "Venue"],
    "Jeep": ["Cherokee", "Compass", "Gladiator", "Grand Cherokee", "Wrangler", "Renegade"],
    "Kia": ["K5", "Niro", "Seltos", "Sorento", "Sportage", "Telluride", "Forte", "Rio"],
    "Land Rover": ["Defender", "Discovery", "Evoque", "Range Rover", "Sport"],
    "Lexus": ["ES", "GX", "IS", "LX", "NX", "RX", "UX"],
    "Lincoln": ["Aviator", "Corsair", "Nautilus", "Navigator"],
    "Mazda": ["CX-3", "CX-30", "CX-5", "CX-9", "Mazda3", "Mazda6", "MX-5 Miata"],
    "Mercedes-Benz": ["A-Class", "C-Class", "CLA", "E-Class", "G-Class", "GLA", "GLB", "GLC", "GLE", "S-Class"],
    "Mitsubishi": ["Eclipse Cross", "Mirage", "Outlander"],
    "Nissan": ["Altima", "Frontier", "Kicks", "Leaf", "Maxima", "Pathfinder", "Rogue", "Sentra", "Titan", "Versa"],
    "Ram": ["1500", "2500", "3500", "ProMaster"],
    "Subaru": ["Ascent", "Crosstrek", "Forester", "Impreza", "Legacy", "Outback"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y", "Cybertruck"],
    "Toyota": ["4Runner", "Camry", "Corolla", "Highlander", "Prius", "RAV4", "Sequoia", "Sienna", "Tacoma", "Tundra"],
    "Volkswagen": ["Atlas", "Golf", "Jetta", "Passat", "Taos", "Tiguan"],
    "Volvo": ["S60", "S90", "V60", "XC40", "XC60", "XC90"]
  };

  var MAKES = Object.keys(VEHICLES);

  function fillDatalist(dlId, values) {
    var dl = document.getElementById(dlId);
    if (!dl) return;
    dl.innerHTML = "";
    values.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      dl.appendChild(o);
    });
  }

  function currentModels() {
    var key = MAKES.find(function (m) { return m.toLowerCase() === (makeInput.value || "").trim().toLowerCase(); });
    return key ? VEHICLES[key] : [];
  }

  function refreshModels() {
    var models = currentModels();
    fillDatalist("models", models);
    if (modelInput && models.indexOf(modelInput.value) === -1) {
      modelInput.value = "";
    }
  }

  var makeInput = document.getElementById("make");
  var modelInput = document.getElementById("model");

  if (makeInput) {
    fillDatalist("makes", MAKES);
    makeInput.addEventListener("input", refreshModels);
  }

  var issueInput = document.getElementById("issue_desc");

  var SAMPLES = {
    "brakes": "Customer reports a squealing noise when braking, mostly in the mornings. Intermittent vibration in the steering wheel at highway speed.",
    "engine": "Check engine light is on. Car hesitates and stumbles when accelerating uphill. Smells like rotten eggs sometimes.",
    "ac": "A/C blows warm air on the driver's side. Coolant lines seem okay, no visible leaks. Happens at idle and while driving.",
    "no-start": "Car cranks but won't start. Battery seems fine. It happened twice this week and now it won't start at all.",
    "electrical": "Headlights flicker and the radio cuts out when driving over bumps. Battery was replaced last year. Sometimes doors lock by themselves.",
    "suspension": "Front end rattles over bumps and the steering pulls to the right. Seems worse at highway speed.",
    "tires": "Steering wheel vibrates starting around 55 mph. One front tire is wearing unevenly on the inner edge.",
    "body": "Rear driver-side door was lightly hit in a parking lot. Dent with scratched paint; door still opens and closes fine."
  };

  var HINTS = {
    "brakes": ["Brake pads & rotors", "Brake fluid & lines", "Caliper condition"],
    "engine": ["O2 sensors / catalytic", "Spark plugs & coils", "Fuel system check"],
    "ac": ["Refrigerant charge", "Compressor & clutch", "Condenser & fans"],
    "electrical": ["Battery & alternator", "Starter circuit / wiring", "Fuses & relays"],
    "suspension": ["Shocks & struts", "Ball joints & bushings", "Wheel alignment"],
    "no-start": ["Battery & connections", "Starter motor", "Fuel delivery & sensors"],
    "tires": ["Tire condition & balance", "Wheel alignment", "TPMS sensors"],
    "body": ["Panel repair / paint", "Impact parts & lights", "Frame inspection"]
  };

  var activeSymptom = "brakes";

  function applySymptom(key) {
    activeSymptom = key;
    document.querySelectorAll(".symptom").forEach(function (s) {
      s.classList.toggle("active", s.getAttribute("data-symptom") === key);
    });
    if (issueInput) issueInput.value = SAMPLES[key];
    var hints = HINTS[key] || [];
    document.querySelectorAll(".live-note span").forEach(function (el, i) {
      el.textContent = hints[i] || "";
    });
  }

  document.querySelectorAll(".symptom").forEach(function (s) {
    s.addEventListener("click", function () { applySymptom(s.getAttribute("data-symptom")); });
  });

  document.querySelectorAll(".rate-chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.querySelectorAll(".rate-chip").forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      document.getElementById("labor_rate").value = chip.getAttribute("data-rate");
      document.getElementById("tax_rate").value = chip.getAttribute("data-tax");
    });
  });

  // live preview
  function setVal(id, selector) {
    var el = document.getElementById(id);
    var v = (el ? el.value : "").trim();
    document.querySelector(selector).textContent = v || "—";
  }
  function livePreview() {
    setVal("customer_name", "#pv-name");
    var mk = document.getElementById("make").value.trim();
    var mo = document.getElementById("model").value.trim();
    var yr = document.getElementById("year").value.trim();
    document.querySelector("#pv-vehicle").textContent =
      [yr, mk, mo].filter(function (x) { return x; }).join(" ") || "Make · Model";
    var issue = issueInput ? issueInput.value.trim() : "";
    document.querySelector("#pv-issue").textContent = issue || "The customer's complaint will appear here…";
  }
  document.querySelectorAll("#customer_name, #make, #model, #year, #mileage, #issue_desc").forEach(function (el) {
    el.addEventListener("input", livePreview);
  });

  if (issueInput) {
    var oldIssue = issueInput.value.trim();
    if (oldIssue) {
      var matched = null;
      Object.keys(SAMPLES).forEach(function (k) { if (SAMPLES[k] === oldIssue) matched = k; });
      if (matched) applySymptom(matched);
    }
  }

  var fillBtn = document.getElementById("fill-example");
  if (fillBtn) {
    fillBtn.addEventListener("click", function () {
      document.getElementById("customer_name").value = "Maria Gonzalez";
      makeInput.value = "Toyota";
      modelInput.value = "Corolla";
      document.getElementById("year").value = "2015";
      document.getElementById("mileage").value = "128,000";
      applySymptom("engine");
      refreshModels();
      livePreview();
    });
  }

  var copyBtn = document.getElementById("copy-message");
  if (copyBtn) {
    var msgEl = document.getElementById("customer-msg");
    copyBtn.addEventListener("click", function () {
      var text = msgEl ? msgEl.textContent : "";
      function done() {
        var original = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        setTimeout(function () { copyBtn.textContent = original; }, 1600);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () { fallbackCopy(text); done(); });
      } else {
        fallbackCopy(text);
        done();
      }
    });
  }

  var copyShare = document.getElementById("copy-share");
  if (copyShare) {
    copyShare.addEventListener("click", function () {
      var urlEl = document.getElementById("share-url");
      var text = urlEl ? urlEl.value : "";
      function done() {
        var original = copyShare.textContent;
        copyShare.textContent = "Copied!";
        setTimeout(function () { copyShare.textContent = original; }, 1600);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () { fallbackCopy(text); done(); });
      } else {
        fallbackCopy(text);
        done();
      }
    });
  }

  var printBtn = document.getElementById("print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", function () { window.print(); });
  }
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  }

  var modal = document.getElementById("sample-modal");
  var showSample = document.getElementById("show-sample");
  if (modal && showSample) {
    showSample.addEventListener("click", function () { modal.hidden = false; document.body.classList.add("modal-open"); });
    modal.querySelectorAll("[data-close-modal]").forEach(function (el) {
      el.addEventListener("click", function () { modal.hidden = true; document.body.classList.remove("modal-open"); });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) { modal.hidden = true; document.body.classList.remove("modal-open"); }
    });
  }

  var dashSearch = document.getElementById("dash-search");
  var filterChips = document.querySelectorAll("#dash-filters .filter-chip");
  var dashRows = document.querySelectorAll(".dash-table tbody tr[data-status]");
  var dashEmpty = document.getElementById("dash-empty");
  var activeDashFilter = "all";

  function applyDashFilter(query) {
    var q = (query || "").toLowerCase();
    var visible = 0;
    dashRows.forEach(function (row) {
      var status = row.getAttribute("data-status");
      var matchFilter = activeDashFilter === "all" || status === activeDashFilter;
      var matchQuery = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
      var show = matchFilter && matchQuery;
      row.style.display = show ? "" : "none";
      if (show) visible++;
    });
    if (dashEmpty) {
      dashEmpty.classList.toggle("hidden", visible !== 0);
      dashEmpty.textContent = activeDashFilter === "all"
        ? "No estimates match your search."
        : "No " + activeDashFilter + " estimates match.";
    }
  }

  if (dashSearch) dashSearch.addEventListener("input", function () { applyDashFilter(dashSearch.value); });
  filterChips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      filterChips.forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      activeDashFilter = chip.getAttribute("data-filter");
      if (dashSearch) applyDashFilter(dashSearch.value);
      else applyDashFilter("");
    });
  });
});