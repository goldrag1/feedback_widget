app_name = "feedback_widget"
app_title = "Feedback Widget"
app_publisher = "DCNet"
app_description = (
    "Drop-in floating feedback widget with element pointer + tag chips + context bundle. "
    "Stores comments as Feedback Comment DocType and mirrors raw payload to "
    "sites/<site>/private/feedback/<project>.jsonl for AI coding agents."
)
app_email = "dev@dcnet.local"
app_license = "ISC"
app_version = "1.1.0"

# Bundle that auto-mounts the widget on every desk page with Frappe-aware
# callbacks. Cache-bust via content hash from assets.json — no ?version= suffix.
app_include_js = ["feedback_widget.bundle.js"]
