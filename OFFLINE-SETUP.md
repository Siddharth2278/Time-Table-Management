# CampusGrid Timetable

This is an offline desktop application. It does not need a server, database connection, or internet access to open the timetable studio and upload a format photo.

## Build the Windows installer

From the project folder, run:

```powershell
npm install
npm run build:win
```

The generated installer and portable executable are placed in `dist/`. Copy the installer to the college PC and install it normally. The installer creates a desktop shortcut named **CampusGrid Timetable**.

## Run during development

```powershell
npm start
```