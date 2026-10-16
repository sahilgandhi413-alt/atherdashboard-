# Assets Folder - Custom Images

This folder contains the custom images used in the Ather Dashboard.

## 📸 Current Images

### 1. **logo.jpg** ✅
- **Source**: images.jfif (from Desktop)
- **Size**: 227x222 pixels
- **Used in**: 
  - Banner header logo
  - Sidebar branding
  - Closing banner

### 2. **scooter.jpg** ✅
- **Source**: images 2.jfif (from Desktop)
- **Size**: 447x447 pixels
- **Used in**:
  - Banner right side (scooter illustration)
  - Model cards
  - Sidebar artwork

### 3. **hero.jpg** (Optional)
- **Status**: Not provided (using default SVG skyline)
- **Recommended Size**: 1920x400px or wider
- **Usage**: Banner background image

## 🎨 How Images Are Used

The dashboard automatically detects and uses these images:

1. **Logo Image** (`logo.jpg`)
   - Replaces the default SVG Ather logo
   - Shows in banner (80x80px) and sidebar (40x40px)
   - Automatically scaled to fit

2. **Scooter Image** (`scooter.jpg`)
   - Replaces the default SVG scooter illustration
   - Used in banner (138px height) and model cards
   - Automatically scaled to fit

3. **Hero Background** (`hero.jpg`) - Optional
   - If added, replaces the default SVG skyline
   - Should be a wide landscape image
   - City skyline, tech background, or abstract patterns work well

## ✅ What's Working

- ✓ Logo image: **Integrated and working**
- ✓ Scooter image: **Integrated and working**
- ✓ Automatic image detection: **Working**
- ✓ Fallback to SVG: **Working** (for hero.jpg)

## 🚀 How It Works

The dashboard uses the `asset_uri()` function that:
1. Looks for images in this folder
2. Supports formats: .jpg, .jpeg, .png, .webp
3. Converts to base64 data URIs
4. Falls back to SVG graphics if images aren't found

## 📝 File Structure

```
assets/
├── logo.jpg         ✅ Custom Ather logo (227x222)
├── scooter.jpg      ✅ Scooter image (447x447)
└── README.md        📖 This file
```

## 💡 To Add Hero Background

If you want to add a hero background image:

1. Find or create a wide landscape image (1920x400px recommended)
2. Save it as `hero.jpg` in this folder
3. The dashboard will automatically use it on next run

Recommended images:
- City skyline at night
- Technology/circuit board patterns
- Abstract blue/cyan gradients
- Urban mobility scenes

## 🎨 Image Guidelines

**Logo:**
- Keep aspect ratio close to square
- Clear visibility at small sizes
- Works well on dark backgrounds

**Scooter:**
- Side profile view works best
- Clear product visibility
- Works well on dark backgrounds

**Hero:**
- Landscape orientation (wide)
- Not too busy (text readability important)
- Dark tones or can be darkened with overlay

---

**Status**: ✅ Images successfully integrated!
**Last Updated**: October 16, 2026
