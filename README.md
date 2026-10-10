# GOG Galaxy NES Integration

## ✨ Features

* **File Support:** Supports all NES files.

* **Integrated Playtime:** Playtime tracking is directly linked to the GOG system.

* **Emulator Support:** Multiple emulators are supported (Mesen has the best compatibility and it's used as default).

* **Long-Term Maintenance:** Ongoing plugin maintenance with regular updates, new features, and bug fixes.

## 📌 Other emulator plugins

| Integration | Status | Achievements | Game Time | Download |
|-------------|--------|--------------|-----------|----------|
| PS2 | ✅ Released | ⚠️ | ✅ | [Download](https://github.com/Notimagination/galaxy-ps2-integration-renew/tree/main) |
| Switch | ✅ Released | ❌ | ✅ | [Download](https://github.com/Notimagination/galaxy-switch-integration) |
| PSP | ⏳ Planned | ⚠️ | ✅ | Download |
| WII | ⏳ Planned | ⚠️ | ✅ | Download |
| PS3 | ⏳ Planned | ❌ | ✅ | Download |
| Local games | ✅ Released | ❌ | ✅ | [Download](https://github.com/Notimagination/galaxy-localgames-integration/tree/main) |

  > [!NOTE]
  > Some emulators may support achievements through [RetroAchievements](https://retroachievements.org/), provided that GOG decides to integrate with the system. If that ever happens (which I highly doubt), I’ll implement it.

## 📦 Installation Guide

1. Download the `.zip` file from this repository, or you can check the [releases](https://github.com/Notimagination/galaxy-nes-integration/releases) page for the latest updates.
   
   <img width="942" height="382" alt="Captura de pantalla 2026-10-07 095131" src="https://github.com/user-attachments/assets/491dc159-34b5-418b-9635-c7fa30e2f66e" />

2. Extract and move the `NESPlugin` folder to your GOG Galaxy plugins directory:

   ```
   %localappdata%\GOG.com\Galaxy\plugins\installed
   ```

3. Open **GOG Galaxy**, go to **Settings** > **Integrations**, and look for **NES**. Click **Connect**.

   <img width="581" height="300" alt="step1" src="https://github.com/user-attachments/assets/f905206e-f8b2-4223-9a1b-e5fa9d04eef5" />

4. Configure your paths:

  <img width="533" height="1464" alt="step2" src="https://github.com/user-attachments/assets/99866c93-10f8-4510-8f01-4432eeab162e" />

5. Click the **Save config** button and wait for your games to import.

  <img width="1969" height="909" alt="Captura de pantalla 2026-10-08 112358" src="https://github.com/user-attachments/assets/272cd2ac-fb71-403d-868c-05f9dcb2e1a5" />

## 🎮 Requesting Game Additions

If you would like me to add support for a missing game in a future update, please provide the following details:

* **Game Name**
* **CRC**
* **The log file** generated at`%programdata%\GOG.com\Galaxy`(`plugin-nes-167e722f-be59-42a3-8f8a-16ec7745b858.log`)

🎫 **Open a ticket on the [Issues](https://github.com/Notimagination/galaxy-ps2-integration-renew/issues) page**.

If you're having issues, you should check the [PS2 plugin's](https://github.com/Notimagination/galaxy-ps2-integration-renew#-frequently-asked-questions-faq) Q&A. Same questions, same answers.

