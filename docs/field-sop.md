# Field SOP

The laptop already has this repository. Recording does not need a network. The only network call is the optional weather attach.

1. Start the page: `python -m farm_ontology.ui`
2. Open `http://127.0.0.1:8765/`
3. Read the status. Class C is closed. Financial use is false. Soybean is Crop Ontology CO_336.
4. Stand at the sample. Type latitude and longitude from the phone or meter.
5. Type the sample id. Add a photo path, harvest unit, or moisture only when you have them.
6. Type metres only when the device showed metres. Otherwise leave accuracy unknown.
7. Save. The note is written under `field-notes/` on this laptop.
8. Optional: attach weather. That calls Open-Meteo and keeps the JMA MSM grid at 0.05°. The value is the grid cell, not the plant. If the network fails, the observation is still saved and the weather value stays empty.
9. After you look at the row, add a verification note. A feedback note is for what the form should do differently next time.

The command-line shape check that is not his farm:

```powershell
python -m farm_ontology.fieldkit --dry-run --out fixtures\field\dry-run-not-a-farm.json
```

`--dry-run` writes 0° N, 0° E and the note “Not a farm.”
