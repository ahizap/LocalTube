# Implementation Plan: Partially Scanned Folders UI

## Problem Statement
Users want to:
1. See which folders have been partially scanned (not fully processed)
2. Rescan all partially scanned folders with one click
3. Not manually track which folders were cancelled mid-scan

## Current Behavior Analysis
- The system already auto-skips already-processed videos when rescanning
- The `/api/library/folders` endpoint returns folder stats including `has_thumbs` and `has_previews`
- A folder is "partially scanned" when: `has_thumbs + has_previews < count` (some videos processed, some not)

## Implementation Plan

### Phase 1: Backend Enhancement

#### 1.1 Add "partially_scanned" flag to library folders API
**File:** `backend/main.py` - modify `get_library_folders()`

Add a new field `partially_scanned: bool` to each folder:
```python
folder_map[folder] = {
    "path": folder, 
    "count": total_videos,
    "has_thumbs": videos_with_thumbnails,
    "has_previews": videos_with_previews,
    "partially_scanned": has_thumbs + has_previews < count  # NEW
}
```

#### 1.2 Add API endpoint to rescan partially scanned folders
**File:** `backend/main.py` - new endpoint

```python
@app.post("/api/library/rescan-partial")
def rescan_partial_folders(db: Session = Depends(get_db)):
    """Trigger scan for all folders that are partially scanned."""
    # Get all folders with partial scans
    # Return list of directories to rescan
    # Frontend will trigger scans for each
```

### Phase 2: Frontend Enhancement

#### 2.1 Update API service
**File:** `frontend/src/services/api.js`

Add new method:
```javascript
async getPartiallyScannedFolders() {
    const res = await api.get('/library/folders');
    return res.data.filter(f => f.partially_scanned);
}
```

#### 2.2 Add UI indicator in SettingsView
**File:** `frontend/src/views/SettingsView.vue`

1. **Show indicator badge** next to partially scanned folders:
   - Yellow/orange badge: "Partial" 
   - Green badge: "Complete"

2. **Add "Rescan Partial" button**:
   - Located near the library folders section
   - Shows count: "Rescan X Partial Folders"
   - Triggers scan for all partially scanned directories

### Phase 3: Visual Design

#### UI Mockup (Settings View - Library Section)

```
┌─ Library Folders ─────────────────────────────────────┐
│  📁 /movies/action          15 videos  ✓ Complete    │
│  📁 /movies/comedy          12 videos  ⚠ Partial (8/12) │
│  📁 /movies/horror          20 videos  ⚠ Partial (5/20) │
│                                                       │
│  [Rescan 2 Partial Folders]  [Clear Finished Tasks]  │
└───────────────────────────────────────────────────────┘
```

### Files to Modify

| File | Changes |
|------|---------|
| `backend/main.py` | Add `partially_scanned` field + new API endpoint |
| `frontend/src/services/api.js` | Add method to get partial folders |
| `frontend/src/views/SettingsView.vue` | Add indicator badges + rescan button |

### Implementation Order

1. Backend: Add `partially_scanned` field to existing `/api/library/folders`
2. Backend: Create `/api/library/partial-folders` endpoint (or reuse existing with filter)
3. Frontend: Update API service
4. Frontend: Add visual indicator in folder list
5. Frontend: Add "Rescan Partial" button with functionality