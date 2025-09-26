---
title: "TouchDesigner Installation Troubleshooting"
category: "REFERENCE"
document_type: "troubleshooting"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["new_user", "system_administrator", "technical_artist"]
completion_signals: ["can_resolve_installation_issues", "can_diagnose_startup_problems", "understands_licensing_issues"]
operators: []
concepts: ["installation", "troubleshooting", "licensing", "system_requirements", "drivers"]
prerequisites: ["basic_computer_administration"]
workflows: ["initial_setup", "system_maintenance"]
keywords: ["install", "uninstall", "troubleshoot", "license", "drivers", "startup", "windows", "macos"]
tags: ["installation", "troubleshooting", "support", "system", "reference"]
related_docs: ["REF_TouchDesigner_System_Requirements", "REF_Licensing"]
---

# TouchDesigner Installation Troubleshooting

This page provides solutions for dealing with problems during installation, licensing, startup and running of TouchDesigner.

For troubleshooting while working inside TouchDesigner, see the article **Troubleshooting in TouchDesigner**.

## Contents
- [Problems during Installation on Windows OS](#problems-during-installation-on-windows-os)
- [Missing libraries after Installation on Windows OS](#missing-libraries-after-installation-on-windows-os)
- [Problems after installation with licensing or keying](#problems-after-installation-with-licensing-or-keying)
- [Problems during Uninstall](#problems-during-uninstall)
- [Problems during TouchDesigner Startup](#problems-during-touchdesigner-startup)

---

## Problems during Installation on Windows OS

### Installer exits during installation or aborts with an Error

When the Installer exits during Installation without giving a sufficient reason, start a Windows Command Prompt window with Administrator privileges and run:

```cmd
"C:\MyFolder\TouchDesigner0xx.xxxxx.exe" /LOG="example.log"
```

Send the resulting log file as a zip or link including a description of the encountered error to **Derivative Support**.

**Note:** If you persistently run into an issue with the installer, you can try running TouchDesigner without actually installing it. To some extent the installer just copies files to disk and makes sure that some prerequisites are met. All the required files are contained separately in the installer and you can try extracting them using the above mentioned `/Extract` Installer Command-line switch.

The extracted folder structure will contain a `bin` folder in which you can find `TouchDesigner.exe`.

### Installer can't continue because of insufficient access rights to folder

This behavior can happen during the de-installation phase of a previously installed version. The best way around this is to restart your computer and start the installation process again.

### Installer can't remove previous installed TouchDesigner version

In some cases the Installer will quit because it was not able to uninstall a previously installed TouchDesigner version.

**Geekuninstaller**, available from [here](https://geekuninstaller.com/), has had good results when trying to resolve install and uninstall related problems.

If the error is persistent, try re-installing the previously installed version of TouchDesigner, remove it via the Windows "Apps & features" Dialog and try installing the new version again.

---

## Missing libraries after Installation on Windows OS

### Installing missing libraries for Windows N and Windows KN distributions

Windows N and Windows KN versions are made for the European and Korean market and due to antitrust regulations do not include Windows Media Player which parts of are required to run TouchDesigner.

You can download and install the missing features for Windows 10 / 11 [here](https://support.microsoft.com/en-us/help/3145500/media-feature-pack-list-for-windows-n-editions).

---

## Problems after installation with licensing or keying

### Windows - License Retrieval Error

In some cases starting TouchDesigner will fail with a dialog titled **TouchDesigner Key Retrieval Error** or **License Retrieval Error**. The content of the error message will look similar to this:

> License Retrieval Error

This can be resolved by rebuilding the WMI repository.

**Please be advised though that deleting and rebuilding the repository can cause damage to the system or to installed applications.**

To perform a rebuild of the WMI repository, please do the following:

1. Disable and stop the `winmgmt` service
2. Locate `C:\Windows\System32\wbem` and copy the `wbem` to another location for a backup
3. Rename `C:\Windows\System32\wbem\repository` folder (Note: it will not let you rename the folder if `winmngmt` service is still running)
4. Enable and start the `winmgmt` service
5. Open Command Prompt as Administrator, run the following commands:
   ```cmd
   cd C:\Windows\System32\wbem\
   for /f %s in ('dir /b *.mof') do mofcomp %s
   ```

If you continue to have problems, join the support thread [here](https://forum.derivative.ca).

### macOS - Permissions Error when installing or disabling a key

If you get a **L1 Key Error** when installing your key, or if you get an error disabling your key, please follow these instructions. Please make sure you are in an Administrator account.

In your admin account, open Terminal and paste in the command:

```bash
ls -l -d "/Library/Application Support/ca.derivative"
```

You should get a line back like so. Note that the group owner should be `admin`, not `wheel`:

```
drwxrwxr-x@ 10 root admin 340 17 Jan 2017 /Library/Application Support/ca.derivative
```

If you are missing the directory, then enter this command in the Terminal:

```bash
sudo mkdir "/Library/Application Support/ca.derivative"
```

If you do not have matching permissions (1st column), then enter this command in the Terminal:

```bash
sudo chmod 775 "/Library/Application Support/ca.derivative"
```

If you have `wheel` instead of `admin` as group owner (4th column), then enter this command in the Terminal:

```bash
sudo chgrp -R admin "/Library/Application Support/ca.derivative"
```

Restart TouchDesigner and try installing or disabling the key again.

### Firewall Issues

If the Key Manager is giving connection errors, it may be due to a firewall blocking access to our key server. Ensure TCP connections to both `www.derivative.ca` and `derivative.ca` on port 443 is allowed through your firewall.

### Proxy Server

TouchDesigner currently does not make use of proxy server configurations that your system may be using. You'll need to use the **Offline key generation method** if your connection requires a proxy server.

---

## Problems during Uninstall

### Installer exits during Uninstall without error

When this happens, best practice has been to restart the computer to free up any possible locks on the folder. Most commonly after a restart the remaining files will have been removed and a fresh install can be started.

---

## Problems during TouchDesigner Startup

### System Requirements

Confirm that your computer meets **TouchDesigner's System Requirements**.

### Graphics/GPU Drivers - Windows Only

If TouchDesigner does not start at all, or opens and then closes, crashes, or presents an empty screen, the first thing to check is your graphics drivers. Always install the latest graphics drivers from Nvidia, AMD or Intel websites directly. **Do not use laptop or system manufacturer drivers** as they are often months or years out of date.

- **[Nvidia Drivers](https://www.nvidia.com/drivers/)**
- **[AMD Drivers](https://www.amd.com/support/)**
- **[Intel Drivers](https://www.intel.com/content/www/us/en/support/)**

**Note:** It is recommended to keep graphics drivers generally up to date. If you install a newer version of TouchDesigner and start experiencing issues, try updating your graphics drivers if you have not done so recently.

### OS Updates

Make sure all OS updates are applied to your system.

- On **Windows**: go to Settings > Windows Update and check for new updates available
- On **macOS**: go to System Settings > General > Software Update

### Common Bloatware Issues

Many systems come with additional software from the manufacturer that may cause performance problems or instabilities. This is most common on laptops, but prebuilt desktops also will ship with such 'bloatware'. If you have experienced crashing on startup, crashing while opening separate windows, random performance spikes, window not responding, it is worth looking for bloatware that might be affecting TouchDesigner.

#### Solutions:

1. **Identify and Remove** - Review the applications installed on your system in Settings > Apps > Installed Apps. Try uninstalling unidentified applications to see if it fixes the problem.

2. **New Windows Install** - If possible, when setting up a new machine install Windows using a new download from Microsoft. This is an especially good practice for systems that require maximum performance, up-time and long-term reliability. For these systems you will want the minimum number of extraneous programs and services running, so a fresh Windows install is the best starting point.

3. **Forum support threads** - There are numerous discussions in the forum on this topic that might help identify the issue on your system. Search for 'bloatware' in the forum.

#### Common Issues and Forum Links:

- **Crashes when opening on second window** - [thread#138178](https://forum.derivative.ca/t/138178), [thread#151606](https://forum.derivative.ca/t/151606), [thread#224073](https://forum.derivative.ca/t/224073), [thread#210237](https://forum.derivative.ca/t/210237)
- **Window doesn't open OR TD runs in background but no window** - [thread#350229](https://forum.derivative.ca/t/350229), [thread#319413](https://forum.derivative.ca/t/319413)

---

## See Also

- **TouchDesigner System Requirements**
- **Troubleshooting in TouchDesigner**
- **Derivative Support Forum**