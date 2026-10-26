/* config.js - settings and PROVISIONAL option lists.
   IMPORTANT: category, candidate-type and branch lists below are placeholders typed by hand.
   In Stages 7-9 they will be replaced by lists taken from official CET Cell data. */
window.APP_CONFIG = {
  DATA_MODE: "static",       // "static" = the browser loads published data files and runs the engine itself (chosen design).
  DATA_BASE_URL: "data/",    // folder of the published data files, relative to the page. Can be changed to your own hosting later.
  API_URL: "",               // optional: Apps Script address (only used if DATA_MODE is "api"; not needed for the static design).
  candidateTypes: [
    "Maharashtra State candidate",
    "All India candidate",
    "Other Than Maharashtra (OMS) candidate"
  ],
  categories: [
    "Open", "OBC", "SC", "ST", "VJ/DT-A", "NT-B", "NT-C", "NT-D", "SBC", "EWS"
  ],
  extraEligibility: [
    { id: "tfws", label: "Applying for TFWS (Tuition Fee Waiver Scheme) seats" },
    { id: "defence", label: "Defence-category claim" },
    { id: "pwd", label: "Person with Disability (PWD) claim" }
  ],
  genders: ["Female", "Male", "Other / prefer not to say"],
  branches: [
    "Computer Science and Engineering",
    "Computer Engineering",
    "Information Technology",
    "Artificial Intelligence and Data Science",
    "Artificial Intelligence and Machine Learning",
    "Electronics and Telecommunication Engineering",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
    "Instrumentation Engineering",
    "Other branch (from official data later)"
  ],
  // Current official names; older names shown in brackets so students recognise them.
  districts: [
    "Ahilyanagar (Ahmednagar)", "Akola", "Amravati", "Chhatrapati Sambhajinagar (Aurangabad)",
    "Beed", "Bhandara", "Buldhana", "Chandrapur", "Dhule", "Gadchiroli", "Gondia", "Hingoli",
    "Jalgaon", "Jalna", "Kolhapur", "Latur", "Mumbai City", "Mumbai Suburban", "Nagpur",
    "Nanded", "Nandurbar", "Dharashiv (Osmanabad)", "Nashik", "Palghar", "Parbhani", "Pune",
    "Raigad", "Ratnagiri", "Sangli", "Satara", "Sindhudurg", "Solapur", "Thane", "Wardha",
    "Washim", "Yavatmal"
  ],
  priorities: [
    { id: "placements", label: "Good placements" },
    { id: "teaching", label: "Good teaching" },
    { id: "infrastructure", label: "Good infrastructure" },
    { id: "low_fees", label: "Lower fees" },
    { id: "admission_chance", label: "Higher admission probability" }
  ]
};
