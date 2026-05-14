---
description: Synchronizes the local project directory to the Raspberry Pi
---

# Title: Sync Mikabox Device
# Description: Syncs the local device code to the Raspberry Pi

1. Verify that the local directory structure is ready for deployment.
2. Ensure SSH connection to the target Raspberry Pi is active.
3. Execute the rsync command to transfer files:
   rsync -avz --delete ~/my_projects/mikabox/device  user@pi4:/home/mikabox/device
4. Confirm successful transfer and notify of completion.