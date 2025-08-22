# Bump Animation Testing Guide

## Animation Sequence Restored

The complete bump animation sequence has been restored:

### 1. **Elevate** (140ms)
- Card lifts up with scaling and shadow
- CSS class: `bumpElevate`
- Keyframe: `bumpElevate` with scale and translateY

### 2. **Wiggle** (240ms) 
- Card wiggles side to side while elevated
- CSS class: `bumpWiggle` 
- Keyframe: `bumpWiggle` with rotation

### 3. **Fly** (520ms)
- Card flies smoothly to Doing column
- Creates a clone element that animates across screen
- Original card fades out with `bumpFading`
- Clone is removed after animation completes

### 4. **State Change**
- Task status updated to "doing"
- Card appears in Doing column

## Fixes Applied

### CSS Animation Issues Fixed:
- ✅ `bumpWiggle` now uses correct keyframe (was using `bumpShake`)
- ✅ `bumpElevate` now uses proper keyframe animation
- ✅ CSS variables properly defined

### Event Handling Fixed:
- ✅ Button clicks properly isolated from drag events
- ✅ Card element reference improved (fallback to closest `.card`)
- ✅ Enhanced debugging logs added

### Animation Flow Fixed:
- ✅ Proper timing: 140ms → 240ms → 520ms
- ✅ Class removal between stages
- ✅ Anchor element reference validation

## Testing Instructions

1. **Open Browser Console** to see debug logs
2. **Navigate to** `http://localhost:3000`
3. **Find tasks in Ready column** (should have Bump buttons)
4. **Click Bump button** on a task card

### Expected Console Output:
```
[v0] TaskCard handleBumpClick called for task: [task-id]
[v0] Calling onBump with task ID and element
[v0] handleBump called with taskId: [task-id]
[v0] Starting bump animation sequence
[v0] Stage 1: Adding bumpElevate class
[v0] Stage 2: Switching to bumpWiggle
[v0] Stage 3: Starting fly animation
[v0] Flying to doing column {source: {...}, target: {...}}
[v0] Stage 4: Committing state change
```

### Expected Visual Sequence:
1. **Card elevates** - lifts up with shadow
2. **Card wiggles** - subtle rotation while elevated  
3. **Card flies** - smooth animation to Doing column
4. **Task appears** in Doing column after animation

## Troubleshooting

### If animation doesn't start:
- Check console for click event logs
- Verify `onBump` handler is passed down properly
- Check if card element is found

### If animation stops at elevate/wiggle:
- Check `doingAnchorRef` is available
- Verify Doing column is rendered
- Check CSS keyframes are loaded

### If fly animation doesn't work:
- Check source/target coordinates in console
- Verify `animateFly` function executes
- Check `bumpFlyClone` CSS is applied