# Field SOP

The laptop already has this repository. Recording does not call a weather or map service.

1. Start the page: `cd web` then `npm run dev`
2. Open `http://127.0.0.1:3000/`
3. Read the status. Class C is closed. Financial use is false. Soybean is Crop Ontology CO_336.
4. Stand at the sample. Type latitude and longitude from the phone or meter.
5. Type the sample id. Add a photo path, harvest unit, or moisture only when you have them.
6. Type metres only when the device showed metres. Otherwise leave accuracy unknown.
7. Save. The observation is `field-notes/obs-*.json`. A verification or feedback note is `field-notes/notes/note-*.json`. The page does not call weather.
8. After you look at the row, add a verification note. A feedback note is for what the form should do differently next time.

The command-line shape check that is not his farm:

```powershell
python -m farm_ontology.fieldkit --dry-run --out fixtures\field\dry-run-not-a-farm.json
```

`--dry-run` writes 0° N, 0° E and the note “Not a farm.”
