---
trigger: always_on
---

# Rule: Auto-Sync Mikabox
# Condition: On file change in ~/my_projects/mikabox/device/**
# Action: Trigger /sync-mikabox

Whenever I save a file or modify code within the `device` folder, automatically run the sync workflow to keep the Raspberry Pi updated for testing.