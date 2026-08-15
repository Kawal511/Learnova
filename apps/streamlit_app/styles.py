"""Streamlit-only presentation CSS, kept out of app.py."""

custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

* {
    cursor: url('data:image/svg+xml;utf8,<svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="6" fill="%23ccff00" stroke="black" stroke-width="1"/></svg>') 6 6, auto !important;
}

button:hover, p:hover, li:hover, h1:hover, h2:hover, h3:hover, h4:hover, h5:hover, h6:hover, a:hover, [data-testid="stExpander"] details:hover, [data-baseweb="tab"]:hover {
    cursor: url('data:image/svg+xml;utf8,<svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg"><circle cx="9" cy="9" r="8" fill="%23ccff00" stroke="black" stroke-width="1.5"/></svg>') 9 9, auto !important;
}

.stApp {
    background-color: #ffffff;
    background-image: radial-gradient(#e0e0e0 2px, transparent 2px);
    background-size: 30px 30px;
}

h1, h2, h3, .st-emotion-cache-10trblm h1 {
    font-family: 'Bebas Neue', cursive !important;
    text-transform: uppercase;
    color: #000000 !important;
    letter-spacing: 1px;
}
h1 {
    font-size: 5.5rem !important;
    line-height: 1.1 !important;
    margin-bottom: 0.5rem !important;
}
h2 {
    font-size: 3rem !important;
}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    background-color: #ccff00 !important;
    color: #000000 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    border: 3px solid #000000 !important;
    border-radius: 0px !important;
    box-shadow: 6px 6px 0px #000000 !important;
    transition: all 0.2s ease !important;
    padding: 0.5rem 1.5rem !important;
}

.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translate(3px, 3px) !important;
    box-shadow: 3px 3px 0px #000000 !important;
    color: #000000 !important;
    border-color: #000000 !important;
}

[data-testid="stFileUploadDropzone"] {
    background-color: #ffffff !important;
    border: 3px dashed #000000 !important;
    border-radius: 0px !important;
    box-shadow: 6px 6px 0px #000000 !important;
}

[data-testid="stSidebar"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    border-right: 5px solid #ccff00 !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p {
    color: #ffffff !important;
}

div[role="radiogroup"] label {
    color: #000000 !important;
    font-weight: 600 !important;
}
</style>
<script>
// Auto-reload on 'Importing a module script failed' — happens when the
// Streamlit server restarts after a crash and old JS bundle hashes are stale.
(function() {
    var _reloaded = sessionStorage.getItem('_lr_reload');
    window.addEventListener('unhandledrejection', function(event) {
        var msg = (event.reason && event.reason.message) ? event.reason.message : '';
        if ((msg.includes('Importing a module script failed') ||
             msg.includes('Failed to fetch dynamically imported module')) && !_reloaded) {
            sessionStorage.setItem('_lr_reload', '1');
            window.location.reload();
        }
    });
    // Clear the flag after a successful load so future crashes also auto-reload.
    window.addEventListener('load', function() {
        sessionStorage.removeItem('_lr_reload');
    });
})();
</script>
"""
