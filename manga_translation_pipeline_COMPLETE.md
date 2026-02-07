# 최종 만화 번역 파이프라인 — Production-Ready

> **138개 개선사항**을 모두 포함한 완전한 문서

## 📊 파이프라인 통계

| Stage | 개선사항 |
|-------|----------|
| PRE-PROCESSING | 15개 |
| STAGE ① | 12개 |
| GAP-A | 10개 |
| STAGE ② | 14개 |
| GAP-B | 12개 |
| STAGE ③ | 15개 |
| GAP-C | 10개 |
| STAGE ④ | 18개 |
| POST | 3개 |
| **TOTAL** | **138개** |

---

## PRE-PROCESSING

### 압축된 만화 파일 처리 (CBZ/CBR)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
import zipfile, rarfile, re

def natural_sort_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', s)]

def extract_manga_archive(file_path):
    if file_path.endswith('.cbz') or file_path.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as z:
            files = []
            for info in z.infolist():
                try:
                    name = info.filename
                except:
                    name = info.filename.encode('cp437').decode('utf-8', errors='ignore')
                files.append((name, z.read(info)))
    elif file_path.endswith('.cbr'):
        with rarfile.RarFile(file_path) as r:
            files = [(info.filename, r.read(info)) for info in r.infolist()]
    
    files.sort(key=lambda x: natural_sort_key(x[0]))
    return files
```

### PDF 이미지 추출 실패 (벡터/텍스트 레이어)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
import fitz

def extract_images_from_pdf(pdf_path, dpi=300):
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images
```

### 여러 이미지 형식 혼재 (JPEG/PNG/WebP)

**우선순위**: 🟡 MEDIUM

**해결책**: ① Pillow 최신 버전 → ② 모든 이미지를 RGB로 통일 (alpha channel 제거 후 흰색 배경 합성)

**구현 코드**:

```python
from PIL import Image

def load_and_normalize_image(file_path):
    img = Image.open(file_path)
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    return img
```

### 이중페이지(spread) 분할 오류

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
import cv2, numpy as np

def detect_double_page_gutter(img):
    h, w = img.shape[:2]
    center_strip = img[:, int(w*0.4):int(w*0.6)]
    gray = cv2.cvtColor(center_strip, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    vertical_edges = np.sum(edges, axis=0)
    gutter_x = np.argmax(vertical_edges) + int(w*0.4)
    return gutter_x if vertical_edges.max() / edges.size > 0.1 else w // 2

def split_double_page(img):
    h, w = img.shape[:2]
    if w / h < 1.7: return [img]
    gutter_x = detect_double_page_gutter(img)
    center = img[:, gutter_x-50:gutter_x+50]
    if has_important_content(center): return [img]
    return [img[:, :gutter_x], img[:, gutter_x:]]
```

### 표지·속표지·광고 페이지 제거

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def classify_page_type(img, page_num, total):
    if page_num < 3 or page_num >= total - 3:
        text_ratio = detect_text_area_ratio(img)
        if text_ratio < 0.1: return "cover"
    text_ratio = detect_text_area_ratio(img)
    if text_ratio > 0.3: return "ad"
    return "content"
```

### 페이지 방향 오류 (회전된 페이지)

**우선순위**: 🟠 HIGH

**해결책**: ① Tesseract OSD로 방향 감지 → ② 자동 회전 후 confidence 비교 → ③ 높은 쪽 선택

**구현 코드**:

```python
import pytesseract

def detect_and_fix_orientation(img):
    try:
        osd = pytesseract.image_to_osd(img)
        angle = int(re.search(r'Rotate: (\\d+)', osd).group(1))
        if angle != 0:
            img = img.rotate(angle, expand=True)
    except:
        pass
    return img
```

### 페이지 순서 검증 (메타데이터 불신)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
import imagehash

def verify_page_order(pages):
    for i in range(len(pages) - 1):
        h1 = imagehash.average_hash(pages[i])
        h2 = imagehash.average_hash(pages[i+1])
        similarity = 1 - (h1 - h2) / 64.0
        if similarity < 0.3:
            print(f"Warning: Pages {i} and {i+1} are very different")
```

### 저해상도 스캔 (< 150 DPI)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
import cv2
from PIL import Image, ImageFilter

def upscale_low_resolution(img, target_dpi=300):
    current_dpi = estimate_dpi(img)
    if current_dpi >= target_dpi: return img
    
    scale = target_dpi / current_dpi
    h, w = img.shape[:2]
    
    if current_dpi < 150:
        print(f"Warning: Very low DPI ({current_dpi})")
        add_to_manual_review("low_dpi", img)
    
    img_pil = Image.fromarray(img)
    img_pil = img_pil.resize((int(w*scale), int(h*scale)), Image.BICUBIC)
    img_pil = img_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
    return np.array(img_pil)
```

### 배경 노이즈 (종이 질감, 얼룩, 그림자)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
import cv2, numpy as np

def remove_background_noise(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    kernel = np.ones((3, 3), np.uint8)
    opened = cv2.morphologyEx(blurred, cv2.MORPH_OPEN, kernel)
    shadow_free = cv2.divide(gray, blurred, scale=255)
    _, normalized = cv2.threshold(shadow_free, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return normalized
```

### JPEG 압축 아티팩트 (블록 노이즈)

**우선순위**: 🟠 HIGH

**해결책**: ① Non-local means denoising → ② Bilateral filter (edge 보존) → ③ 가능하면 PNG 요청

**구현 코드**:

```python
import cv2

def remove_jpeg_artifacts(img):
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    smooth = cv2.bilateralFilter(denoised, 9, 75, 75)
    return smooth
```

### 이미지 크기 불일치 (해상도 제각각)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def normalize_page_sizes(pages):
    max_height = max(p.shape[0] for p in pages)
    normalized = []
    for page in pages:
        h, w = page.shape[:2]
        if h < max_height:
            scale = max_height / h
            new_w = int(w * scale)
            resized = cv2.resize(page, (new_w, max_height))
            normalized.append(resized)
        else:
            normalized.append(page)
    return normalized
```

### 색상 밸런스 불균형 (스캔마다 색감 다름)

**우선순위**: ⚪ LOW

**해결책**: ① 색상 히스토그램 분석 → ② 평균 밝기·대비 정규화 → ③ White balance 자동 조정

**구현 코드**:

```python
import cv2

def normalize_color_balance(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
```

### 컬러 vs 흑백 만화 자동 감지

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
import numpy as np

def detect_color_mode(img):
    std_r, std_g, std_b = [np.std(img[:,:,i]) for i in range(3)]
    if std_r < 10 and std_g < 10 and std_b < 10:
        return "grayscale"
    return "color"
```

### 흑백 반전 페이지 (네거티브)

**우선순위**: 🟠 HIGH

**해결책**: ① 페이지 평균 밝기 계산 → ② < 128이면 반전 → ③ 색상 반전 (255 - pixel) 후 OCR

**구현 코드**:

```python
def detect_and_fix_inverted_page(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean = np.mean(gray)
    if mean < 128:
        img = 255 - img
    return img
```

### 투명 배경 처리 (PNG alpha)

**우선순위**: ⚪ LOW

**해결책**: 이미 pre-3에서 처리 (RGBA → RGB 흰색 배경 합성)

**구현 코드**:

```python
# 이미 pre-3 load_and_normalize_image()에서 구현됨
```

## STAGE ① — 영역 감지

### 배경 없는 칸 (borderless panels)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
from sklearn.cluster import DBSCAN
import numpy as np

def detect_panels_by_text_clustering(text_regions):
    if len(text_regions) == 0: return []
    centers = np.array([[r.x + r.width/2, r.y + r.height/2] for r in text_regions])
    clustering = DBSCAN(eps=200, min_samples=1).fit(centers)
    labels = clustering.labels_
    
    panels = []
    for label in set(labels):
        if label == -1: continue
        cluster = [r for i, r in enumerate(text_regions) if labels[i] == label]
        min_x, min_y = min(r.x for r in cluster), min(r.y for r in cluster)
        max_x, max_y = max(r.x + r.width for r in cluster), max(r.y + r.height for r in cluster)
        panels.append({"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y})
    return panels
```

### 겹치는 칸 (overlapping panels)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def filter_overlapping_panels(panels):
    filtered = []
    for i, panel_i in enumerate(panels):
        is_contained = False
        for j, panel_j in enumerate(panels):
            if i == j: continue
            if (panel_i.x >= panel_j.x and panel_i.y >= panel_j.y and
                panel_i.x + panel_i.width <= panel_j.x + panel_j.width and
                panel_i.y + panel_i.height <= panel_j.y + panel_j.height):
                is_contained = True
                break
        if not is_contained: filtered.append(panel_i)
    return filtered
```

### 비정형 칸 (irregular shaped panels)

**우선순위**: 🟠 HIGH

**해결책**: ① YOLO bbox 후 contour detection으로 정확한 경계 추출 → ② mask 생성해 칸 내부만 인정

**구현 코드**:

```python
import cv2

def refine_panel_boundary(img, bbox):
    x, y, w, h = bbox
    roi = img[y:y+h, x:x+w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0: return bbox
    largest = max(contours, key=cv2.contourArea)
    mask = np.zeros_like(gray)
    cv2.drawContours(mask, [largest], -1, 255, -1)
    return {"bbox": bbox, "mask": mask}
```

### splash page vs 단일 칸 구분

**우선순위**: 🟡 MEDIUM

**해결책**: ① 칸=1일 때 텍스트 밀도 계산 → ② 5% 이상이면 단일 칸 → ③ 5% 미만이면 splash

**구현 코드**:

```python
def classify_single_panel_page(img, panel, text_regions):
    page_area = img.shape[0] * img.shape[1]
    text_area = sum(r.width * r.height for r in text_regions)
    density = text_area / page_area
    return "single_panel" if density > 0.05 else "splash"
```

### 효과음(SFX) 감지 실패 (아티스틱 폰트)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def detect_sfx_with_low_confidence(img, model, conf=0.3):
    results = model(img, conf=conf)
    sfx = []
    for det in results.xyxy[0]:
        x1, y1, x2, y2, conf, cls = det
        if cls == 2 and conf > 0.3:  # SFX class
            sfx.append({"x": int(x1), "y": int(y1), "width": int(x2-x1), "height": int(y2-y1)})
    return sfx
```

### 후리가나(furigana) 감지 실패

**우선순위**: 🟠 HIGH

**해결책**: ① 텍스트 감지 후 '상단에 작은 텍스트' 추가 검사 → ② 대화 bbox 위 30px 별도 OCR

**구현 코드**:

```python
def detect_furigana_above_dialogue(img, dialogue_bbox):
    x, y, w, h = dialogue_bbox
    if y < 30: return None
    furigana_roi = img[max(0, y-30):y, x:x+w]
    gray = cv2.cvtColor(furigana_roi, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    text_ratio = np.sum(binary > 0) / binary.size
    if text_ratio > 0.1:
        return {"x": x, "y": max(0, y-30), "width": w, "height": 30, "type": "furigana"}
    return None
```

### 배경과 겹친 텍스트 (복잡한 배경)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def filter_false_positive(img, candidates):
    valid = []
    for c in candidates:
        roi = img[c.y:c.y+c.h, c.x:c.x+c.w]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        if edge_density > 0.4:  # 배경일 가능성
            text = ocr.read(roi)
            if text.confidence < 0.5: continue
        valid.append(c)
    return valid
```

### 텍스트 영역 경계 불완전 (일부만 감지)

**우선순위**: 🟡 MEDIUM

**해결책**: ① bbox 자동 확장 (padding +10px) → ② morphological dilation → ③ contour로 재계산

**구현 코드**:

```python
def expand_text_bbox(bbox, padding=10):
    x, y, w, h = bbox
    return {
        "x": max(0, x - padding),
        "y": max(0, y - padding),
        "width": w + 2 * padding,
        "height": h + 2 * padding
    }
```

### 세로 스크롤 만화(webtoon) 읽기 순서

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def determine_reading_mode(img):
    h, w = img.shape[:2]
    return "vertical_scroll" if h / w > 2.0 else "horizontal"

def sort_panels(panels, img):
    mode = determine_reading_mode(img)
    if mode == "vertical_scroll":
        return sorted(panels, key=lambda p: p.y)
    return sorted(panels, key=lambda p: (p.y, -p.x))
```

### 같은 행(row) 판단 임계값

**우선순위**: 🟡 MEDIUM

**해결책**: ① 페이지 높이 비율로 설정 (height × 0.05) → ② 또는 칸 높이 평균값

**구현 코드**:

```python
def group_panels_by_row(panels, img):
    h, w = img.shape[:2]
    threshold = h * 0.05
    rows = []
    for p in sorted(panels, key=lambda p: p.y):
        if not rows or abs(p.y - rows[-1][0].y) > threshold:
            rows.append([p])
        else:
            rows[-1].append(p)
    for row in rows: row.sort(key=lambda p: -p.x)
    return [p for row in rows for p in row]
```

### 대각선 레이아웃 (diagonal layout)

**우선순위**: 🟡 MEDIUM

**해결책**: ① 칸 간 시각적 연결성 분석 (가장 가까운 이웃) → ② graph traversal로 순서 결정

**구현 코드**:

```python
from scipy.spatial import distance

def sort_by_visual_flow(panels):
    if len(panels) == 0: return []
    centers = [(p.x + p.width/2, p.y + p.height/2) for p in panels]
    sorted_panels = [panels[0]]
    remaining = list(range(1, len(panels)))
    
    while remaining:
        last_center = centers[panels.index(sorted_panels[-1])]
        distances = [distance.euclidean(last_center, centers[i]) for i in remaining]
        nearest = remaining[np.argmin(distances)]
        sorted_panels.append(panels[nearest])
        remaining.remove(nearest)
    return sorted_panels
```

### 칸 내부 텍스트 읽기 순서 (intra-panel)

**우선순위**: 🟡 MEDIUM

**해결책**: ① 칸 내부 텍스트를 읽기 순서 정렬 → ② 타입별 우선순위 (나레이션 0, 대화 1, SFX 2)

**구현 코드**:

```python
def sort_text_within_panel(text_regions):
    priority = {"narration": 0, "dialogue": 1, "SFX": 2}
    return sorted(text_regions, key=lambda r: (priority.get(r.type, 1), r.y, -r.x))
```

## GAP-A — 말풍선 경계

### 말풍선 없는 텍스트 (floating text)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def get_text_placement_area(text_region, img):
    text_type = text_region.type
    if text_type in ['dialogue']:
        balloon = detect_balloon_around_text(img, text_region)
        return balloon.interior_area if balloon else text_region.bbox
    elif text_type in ['narration', 'thought']:
        return expand_bbox(text_region.bbox, margin=10)
    else:  # SFX
        return None  # 자유 배치
```

### 투명/연한 말풍선 (low contrast)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def detect_balloon_adaptive(img, text_bbox):
    x, y, w, h = text_bbox
    margin = 50
    roi = img[max(0,y-margin):min(img.shape[0],y+h+margin),
              max(0,x-margin):min(img.shape[1],x+w+margin)]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    for threshold in [50, 100, 150]:
        edges = cv2.Canny(gray, threshold, threshold * 2)
        kernel = np.ones((5,5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 100 and point_in_contour((x+w//2, y+h//2), cnt):
                return cnt
    return None
```

### 여러 텍스트 공유 말풍선 (multi-text balloon)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def deduplicate_balloons(balloons, iou_threshold=0.8):
    unique = []
    for balloon in balloons:
        is_duplicate = False
        for unique_balloon in unique:
            iou = calculate_iou(balloon.bbox, unique_balloon.bbox)
            if iou > iou_threshold:
                is_duplicate = True
                unique_balloon.texts.append(balloon.texts[0])
                break
        if not is_duplicate:
            unique.append(balloon)
    return unique
```

### 말풍선 타입 분류 (일반/생각/외침/속삭임)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def classify_balloon_type(contour, edges):
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    convexity = area / hull_area if hull_area > 0 else 0
    
    if convexity < 0.85:
        return "thought"
    elif circularity < 0.6:
        return "shout"
    else:
        return "normal"
```

### 말풍선 vs 효과선 구분

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def is_balloon_not_effect_line(contour):
    area = cv2.contourArea(contour)
    if area < 100:
        return False
    start = contour[0][0]
    end = contour[-1][0]
    distance = np.linalg.norm(start - end)
    perimeter = cv2.arcLength(contour, True)
    if distance / perimeter > 0.1:
        return False  # 열린 선
    return True
```

### 연결된 말풍선 (connected balloons)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def split_connected_balloons(contour, img):
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    threshold = dist.max() * 0.3
    _, waist = cv2.threshold(dist, threshold, 255, cv2.THRESH_BINARY_INV)
    waist = waist.astype(np.uint8)
    if np.sum(waist > 0) > 0:
        mask_without_waist = mask - waist
        separated, _ = cv2.findContours(mask_without_waist, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return separated
    return [contour]
```

### 말풍선 꼬리 손상 (tail damage)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def detect_balloon_tail(contour):
    hull = cv2.convexHull(contour, returnPoints=False)
    defects = cv2.convexityDefects(contour, hull)
    if defects is None:
        return None
    M = cv2.moments(contour)
    cx = int(M['m10'] / M['m00']) if M['m00'] != 0 else 0
    cy = int(M['m01'] / M['m00']) if M['m00'] != 0 else 0
    
    max_defect = None
    max_depth = 0
    for i in range(defects.shape[0]):
        s, e, f, d = defects[i, 0]
        far = tuple(contour[f][0])
        if d > max_depth:
            max_depth = d
            max_defect = far
    return max_defect
```

### 말풍선 내부 마진 계산 (interior margin)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def calculate_adaptive_margin(balloon_area):
    if balloon_area < 5000:
        return 2
    elif balloon_area < 20000:
        return 5
    else:
        return 10

def apply_margin(balloon_contour):
    area = cv2.contourArea(balloon_contour)
    margin = calculate_adaptive_margin(area)
    mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
    cv2.drawContours(mask, [balloon_contour], -1, 255, -1)
    kernel = np.ones((margin*2, margin*2), np.uint8)
    eroded = cv2.erode(mask, kernel, iterations=1)
    return eroded
```

### 불규칙 말풍선 내부 최대 사각형

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def find_inscribed_rectangle(balloon_contour, img_shape):
    mask = np.zeros(img_shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [balloon_contour], -1, 255, -1)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, max_dist, _, max_loc = cv2.minMaxLoc(dist)
    cx, cy = max_loc
    radius = int(max_dist)
    rect_size = int(radius * 1.414)
    return {"x": cx - rect_size//2, "y": cy - rect_size//2, "width": rect_size, "height": rect_size}
```

### 말풍선 경계와 패널 경계 충돌

**우선순위**: ⚪ LOW

**구현 코드**:

```python
def clip_balloon_to_panel(balloon_contour, panel_bbox):
    x, y, w, h = panel_bbox
    clipped_points = []
    for point in balloon_contour:
        px, py = point[0]
        px_clipped = max(x, min(x + w, px))
        py_clipped = max(y, min(y + h, py))
        clipped_points.append([[px_clipped, py_clipped]])
    return np.array(clipped_points, dtype=np.int32)
```

## STAGE ② — OCR

### 저해상도·블러 이미지 (low quality input)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def enhance_text_region(text_roi):
    h, w = text_roi.shape[:2]
    if h < 20 or w < 20:
        scale = max(2, 20 / min(h, w))
        text_roi = cv2.resize(text_roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        text_roi = cv2.filter2D(text_roi, -1, sharpen_kernel)
    return text_roi
```

### 유사 글자 혼동 (similar character confusion)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
import MeCab
mecab = MeCab.Tagger()

def validate_ocr_with_context(text):
    parsed = mecab.parse(text)
    unk_count = parsed.count('UNK')
    if unk_count / len(text.split()) > 0.3:
        alternatives = generate_similar_char_alternatives(text)
        for alt in alternatives:
            if mecab.parse(alt).count('UNK') < unk_count:
                return alt
    return text
```

### 손글씨·아티스틱 폰트 (stylized fonts)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
sfx_dictionary = {'ドキドキ': 'heartbeat', 'ゴゴゴ': 'menacing', 'ドドド': 'rumble'}

def ocr_sfx_with_fallbacks(sfx_img):
    result = manga_ocr.readtext(sfx_img)
    if result.confidence > 0.5:
        return result.text
    for sfx_text in sfx_dictionary:
        if image_similarity(sfx_img, render_text(sfx_text)) > 0.7:
            return sfx_text
    return ask_llm_to_recognize_sfx(sfx_img)
```

### 텍스트 배경 간섭 (background interference)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def remove_background_from_text(text_roi):
    gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    text_on_white = np.ones_like(text_roi) * 255
    text_on_white[binary == 0] = 0
    return text_on_white
```

### 글자 겹침·연결 (overlapping/connected characters)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def separate_connected_chars(text_img):
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3,3), np.uint8)
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    dist = cv2.distanceTransform(opened, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.5 * dist.max(), 255, 0)
    # watershed로 글자 분리
    return separated_chars
```

### 후리가나 분리 및 매칭 (furigana)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def match_furigana_to_kanji(kanji_region, furigana_region):
    kanji_text = ocr(kanji_region.img)
    furigana_text = ocr(furigana_region.img)
    if furigana_region.y + furigana_region.height < kanji_region.y:
        return {"kanji": kanji_text, "furigana": furigana_text, "translate": kanji_text}
    return None
```

### 세로 쓰기 텍스트 (vertical text orientation)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def detect_text_orientation(text_roi):
    h, w = text_roi.shape[:2]
    aspect_ratio = w / h
    if aspect_ratio > 2.0:
        return "horizontal"
    elif aspect_ratio < 0.5:
        return "vertical"
    return detect_char_alignment(text_roi)
```

### 영어·숫자 혼재 텍스트 (mixed language)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
import unicodedata

def normalize_mixed_language_text(text):
    normalized = unicodedata.normalize('NFKC', text)  # 전각→반각
    english_words = re.findall(r'[A-Za-z]+', normalized)
    for word in english_words:
        if word.lower() in english_dictionary:
            normalized = normalized.replace(word, word.capitalize())
    return normalized
```

### 특수 기호·구두점 (special symbols)

**우선순위**: ⚪ LOW

**해결책**: 특수 기호는 유니코드로 정확히 인식 → 번역 시 기호는 보존 → 한국어 번역 후에도 동일 기호 사용

**구현 코드**:

```python
def preserve_special_symbols(text, translation):
    symbols = re.findall(r'[！？…～♡♥★☆※]', text)
    for symbol in symbols:
        if symbol not in translation:
            translation += symbol
    return translation
```

### 다국어 만화 (multilingual comics)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
from langdetect import detect

def detect_and_ocr_multilingual(text_roi):
    result_ja = manga_ocr.readtext(text_roi)
    result_cn = paddle_ocr.ocr(text_roi, lang='ch')
    result_en = pytesseract.image_to_string(text_roi, lang='eng')
    
    results = [(result_ja.text, result_ja.confidence, 'ja'),
               (result_cn[0][1][0], result_cn[0][1][1], 'zh'),
               (result_en, 0.5, 'en')]
    best = max(results, key=lambda x: x[1])
    return {"text": best[0], "language": best[2]}
```

### 회전된 텍스트 (rotated text)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def ocr_with_rotation_correction(text_roi):
    best_result = None
    best_conf = 0
    for angle in [0, 90, 180, 270]:
        rotated = rotate_image(text_roi, angle)
        result = manga_ocr.readtext(rotated)
        if result.confidence > best_conf:
            best_conf = result.confidence
            best_result = result
    return best_result
```

### 오른쪽→왼쪽 쓰기 (RTL languages)

**우선순위**: ⚪ LOW

**해결책**: 언어 감지로 RTL 언어인지 확인 → RTL이면 OCR 결과를 역순으로 정렬

**구현 코드**:

```python
def fix_rtl_text_order(text, language):
    rtl_languages = ['ar', 'he', 'fa']
    if language in rtl_languages:
        words = text.split()
        return ' '.join(reversed(words))
    return text
```

### OCR confidence 임계값 (confidence threshold)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def validate_ocr_confidence(ocr_result, text_type):
    thresholds = {"dialogue": 0.7, "narration": 0.8, "SFX": 0.4, "small_text": 0.6}
    threshold = thresholds.get(text_type, 0.6)
    if ocr_result.confidence >= threshold:
        return ocr_result.text
    else:
        add_to_manual_review("low_confidence", ocr_result, text_type)
        return None
```

### OCR 후 언어 모델 검증 (language model validation)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
import MeCab
mecab = MeCab.Tagger()

def validate_with_language_model(ocr_text):
    parsed = mecab.parse(ocr_text)
    lines = parsed.strip().split('\\n')
    total = len(lines) - 1
    unk_count = sum(1 for line in lines if '\\t' in line and line.split('\\t')[1].startswith('UNK'))
    unk_ratio = unk_count / total if total > 0 else 0
    
    if unk_ratio > 0.3:
        return {"valid": False, "reason": f"Too many unknown words: {unk_ratio:.1%}"}
    return {"valid": True}
```

## GAP-B — 번역 전처리

### 단일 패널 번역 (context loss)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def translate_page_batch(page_texts):
    context = "\\n".join([f"{i+1}. {text.content}" for i, text in enumerate(page_texts)])
    prompt = f"""다음은 만화 한 페이지의 모든 대사입니다. 전체 맥락을 고려하여 번역해주세요.

{context}

번역 결과를 같은 번호로 반환:
"""
    response = llm.complete(prompt)
    translations = parse_numbered_translations(response)
    return translations
```

### 캐릭터 발화 순서 (speaker tracking)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def assign_speaker(text, characters):
    if text.balloon and text.balloon.tail:
        nearest_char = find_nearest_character(text.balloon.tail.direction, characters)
        text.speaker = nearest_char
    return text

def create_prompt_with_speakers(page_texts):
    context = []
    for i, text in enumerate(page_texts):
        speaker = text.speaker if text.speaker else "Unknown"
        context.append(f"{i+1}. [{speaker}]: {text.content}")
    return "\\n".join(context)
```

### 페이지 간 context 연결 (cross-page context)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def translate_with_prev_context(current_page, previous_page, context_size=3):
    prev_context = []
    if previous_page:
        last_texts = previous_page.texts[-context_size:]
        for text in last_texts:
            prev_context.append(f"[이전]: {text.content} → {text.translation}")
    
    prompt = f"""이전 페이지: {chr(10).join(prev_context)}

현재 페이지: {chr(10).join([t.content for t in current_page.texts])}

이전 대사를 참고하여 번역:
"""
    return prompt
```

### 생략된 주어 복원 (omitted subject recovery)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
prompt = """일본어는 주어를 자주 생략하지만, 한국어 번역에서는 맥락상 명확한 경우 주어를 복원하세요.
예시: "好きです" → 이전 대사에서 A가 B에 대해 말하는 중이면 "B를 좋아해요"

대사: {texts}
"""
```

### 캐릭터 이름 불일치 (inconsistent names)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
character_name_dict = {}

def extract_character_name(text):
    names = re.findall(r'[一-龯]{2,4}(?:さん|君|ちゃん|様)?', text)
    for name in names:
        if name not in character_name_dict:
            translated = llm.translate_name(name)
            character_name_dict[name] = translated
    return character_name_dict

def create_prompt_with_dict(texts):
    dict_str = "\\n".join([f"- {ja}: {ko}" for ja, ko in character_name_dict.items()])
    prompt = f"""캐릭터 이름 사전: {dict_str}

위 사전을 참고하여 이름을 일관되게 사용하세요.
"""
    return prompt
```

### 호칭·경어 일관성 (honorifics consistency)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
character_relationships = {
    "佐藤": {"role": "선배", "tone": "formal"},
    "田中": {"role": "친구", "tone": "casual"}
}

def apply_honorifics(name, speaker, listener):
    if listener in character_relationships:
        rel = character_relationships[listener]
        if rel["tone"] == "formal":
            return f"{name} 씨" if rel["role"] != "상사" else f"{name} 님"
        elif rel["tone"] == "casual":
            return name
    return f"{name} 씨"
```

### 전문 용어 사전 (terminology dictionary)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
terminology_dict = {
    "fantasy": {"魔法": "마법", "スキル": "스킬", "レベル": "레벨"},
    "medical": {"手術": "수술", "症状": "증상", "診断": "진단"}
}

def create_prompt_with_terminology(texts, genre):
    if genre in terminology_dict:
        terms = terminology_dict[genre]
        term_str = "\\n".join([f"- {ja}: {ko}" for ja, ko in terms.items()])
        prompt = f"""장르: {genre}. 다음 용어를 일관되게 사용: {term_str}"""
        return prompt
```

### 장르별 번역 톤 (genre-specific tone)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
genre_instructions = {
    "action": "직설적이고 강렬하게. 짧고 임팩트 있는 문장.",
    "romance": "감성적이고 섬세하게. 감정 표현을 풍부하게.",
    "comedy": "유머와 말장난을 살려서.",
    "horror": "긴장감과 불안감 유지."
}

def create_genre_prompt(texts, genre):
    instruction = genre_instructions.get(genre, "자연스럽게 번역")
    prompt = f"""장르: {genre}. 번역 톤: {instruction}

대사: {texts}
"""
    return prompt
```

### 대상 독자층 (target audience)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
audience_instructions = {
    "children": "쉽고 교육적인 표현. 폭력적·선정적 표현 순화.",
    "teen": "현대적이고 생동감 있는 표현. 청소년 언어 반영.",
    "adult": "원문의 뉘앙스를 정확히 전달."
}

def create_audience_prompt(texts, target):
    instruction = audience_instructions.get(target, "")
    prompt = f"""대상 독자: {target}. {instruction}

대사: {texts}
"""
    return prompt
```

### 문화적 맥락 처리 (cultural context)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
prompt = """일본 문화 특유의 표현은 한국 독자가 이해할 수 있도록 자연스럽게 번역하세요.
예시: "お盆" → "명절" 또는 "추석 같은 명절"

대사: {texts}
"""
```

### 번역 길이 예측 (length prediction)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def estimate_max_length(balloon_area, font_size):
    chars_per_line = int(balloon_area.width / (font_size * 0.6))
    max_lines = int(balloon_area.height / (font_size * 1.2))
    return chars_per_line * max_lines

def create_length_prompt(text, max_length):
    prompt = f"""번역 결과는 공백 포함 {max_length}자 이내로 제한하세요.

원문: {text}
번역 (최대 {max_length}자):
"""
    return prompt
```

### API 비용 최적화 (cost optimization)

**우선순위**: ⚪ LOW

**구현 코드**:

```python
def optimize_batch_size(page_texts, max_tokens=4000):
    batches = []
    current_batch = []
    current_tokens = 0
    
    for text in page_texts:
        text_tokens = int(len(text.content) * 1.5)
        if current_tokens + text_tokens > max_tokens:
            batches.append(current_batch)
            current_batch = [text]
            current_tokens = text_tokens
        else:
            current_batch.append(text)
            current_tokens += text_tokens
    
    if current_batch:
        batches.append(current_batch)
    return batches
```

## STAGE ③ — 번역 (LLM)

### 직역 vs 의역 균형 실패 (literal vs free translation)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def create_translation_style_prompt(text, text_type, genre):
    if text_type == "dialogue":
        style = "자연스러운 구어체로 의역하세요. 한국인이 실제로 말하는 방식으로."
    elif text_type == "narration":
        style = "정확하고 문학적으로 직역하세요. 원문의 뉘앙스를 유지."
    elif text_type == "SFX":
        style = "간결하고 리듬감 있게. 2~4음절 의성어/의태어로."
    
    prompt = f"""{genre} 장르 만화입니다.
번역 스타일: {style}

원문: {text}
번역:"""
    return prompt
```

### 대명사 해석 오류 (pronoun resolution)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def resolve_pronouns_in_translation(text, characters_in_context):
    char_info = ", ".join([f"{c.name}({c.gender})" for c in characters_in_context])
    
    prompt = f"""등장 캐릭터: {char_info}

다음 텍스트를 번역할 때, 대명사('彼', '彼女', '그', '그녀')를 문맥상 명확한 캐릭터 이름이나 
적절한 대명사로 해석하세요.

원문: {text}
번역:"""
    return prompt
```

### 존댓말/반말 불일치 (honorific level mismatch)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def apply_honorific_level(speaker, listener, relationship):
    if relationship in ["상사-부하", "선배-후배", "선생-학생"]:
        honorific = "존댓말 사용 (〜요/습니다)"
    elif relationship in ["친구", "동료"]:
        honorific = "반말 사용 (〜야/어)"
    elif speaker.age < listener.age:
        honorific = "존댓말 (나이 차이 고려)"
    else:
        honorific = "적절히 판단"
    
    prompt = f"""화자: {speaker.name}, 청자: {listener.name}
관계: {relationship}
번역 시 {honorific}

원문: {text}"""
    return prompt
```

### 뉘앙스 손실 (nuance loss)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
prompt = """번역 시 다음 뉘앙스를 반드시 유지하세요:
- 추측/불확실: 〜だろう, 〜かもしれない → '~인 것 같다', '~일지도'
- 확신/단정: 〜だ, 〜に違いない → '~이다', '~임에 틀림없다'
- 의무/권유: 〜べき, 〜たほうがいい → '~해야 한다', '~하는 게 좋다'

원문: {text}
번역 (뉘앙스 유지):"""
```

### SFX 번역 품질 (SFX translation quality)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
prompt = """효과음(SFX) 번역 규칙:
1. 간결하게 (2~4음절)
2. 리듬감 유지 (반복 구조)
3. 설명 추가 금지
4. 예시: ドキドキ → 두근두근, ゴゴゴ → 우우웅

원문 SFX: {sfx}
번역:"""
```

### API 호출 비용 폭증 (API cost explosion)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
# 이미 GAP-B에서 구현됨
# 페이지 단위 배치 번역으로 API 호출 최소화
```

### 응답 시간 지연 (response latency)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def optimize_prompt_length(context, max_tokens=4000):
    # 토큰 수 추정
    estimated_tokens = len(context) * 1.5
    
    if estimated_tokens > max_tokens:
        # context 축약
        # 1. 이전 페이지 context: 마지막 3개만
        # 2. 캐릭터 정보: 이름과 성별만
        # 3. 용어집: 자주 나오는 것만
        context = reduce_context(context, max_tokens)
    
    return context
```

### Rate limit 초과 (rate limit exceeded)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
import time

def call_api_with_retry(prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = llm_api.complete(prompt)
            return response
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # exponential backoff: 1, 2, 4, 8, 16초
            print(f"Rate limit hit. Waiting {wait_time}s...")
            time.sleep(wait_time)
```

### LLM 응답 형식 오류 (response format error)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def parse_translation_response(response):
    # Markdown 래핑 제거
    text = response.strip()
    if text.startswith('\`\`\`json'):
        text = text[7:]  # \`\`\`json 제거
    if text.endswith('\`\`\`'):
        text = text[:-3]
    
    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        # 재시도 요청
        return retry_with_format_instruction(response)
```

### 번역 누락 (missing translations)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def validate_translation_completeness(input_texts, translations):
    if len(input_texts) != len(translations):
        missing_indices = []
        for i, text in enumerate(input_texts):
            if i >= len(translations) or translations[i] is None:
                missing_indices.append(i)
        
        # 누락된 것만 재번역
        missing_texts = [input_texts[i] for i in missing_indices]
        retry_translations = llm_api.translate(missing_texts)
        
        # 병합
        for i, idx in enumerate(missing_indices):
            translations.insert(idx, retry_translations[i])
    
    return translations
```

### Hallucination (환각)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
prompt = """**중요**: 원문에 있는 내용만 번역하세요.
- 추가 설명 금지
- 추측 금지
- 원문에 없는 단어 추가 금지

원문: {text}
번역 (원문 충실):"""
```

### 응답 불안정성 (response instability)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
response = llm_api.complete(
    prompt=translation_prompt,
    temperature=0.3,  # 낮은 temperature로 일관성 확보
    seed=42  # 재현 가능성 (OpenAI 지원)
)
```

### 소스 언어 자동 감지 실패 (language detection failure)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
prompt = """다음은 **일본어** 텍스트입니다. **한국어**로 번역하세요.

일본어 원문: {japanese_text}
한국어 번역:"""
```

### 한자 읽기 불일치 (kanji reading inconsistency)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
# 한자 읽기 용어집
kanji_readings = {
    "田中生": "다나카 나마",  # 이름
    "生活": "세이카츠",  # 단어
}

def apply_kanji_reading_context(text):
    for kanji, reading in kanji_readings.items():
        if kanji in text:
            # 용어집의 읽기로 대체
            pass  # 번역 시 참조
    return text
```

### 번역 불가 언어 처리 (untranslatable language)

**우선순위**: ⚪ LOW

**구현 코드**:

```python
def handle_untranslatable(text, language_type):
    if language_type in ["고대 일본어", "방언", "창작 언어"]:
        return {
            "translation": text,  # 원문 그대로
            "note": f"({language_type} - 번역 불가)",
            "status": "untranslatable"
        }
    return standard_translate(text)
```

## GAP-C — 번역 매핑

### 배치 번역 결과 매핑 실패 (batch translation mapping)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def map_translations_to_texts(page_texts, translation_response):
    """배치 번역 결과를 원본 텍스트에 매핑"""
    translations = parse_translation_response(translation_response)
    
    # ID 기반 매핑
    mapping = {}
    for item in translations:
        text_id = item["id"]
        translation = item["translation"]
        mapping[text_id] = translation
    
    # 원본 텍스트에 번역 할당
    for text in page_texts:
        if text.id in mapping:
            text.translation = mapping[text.id]
            text.translation_meta = {"status": "success"}
        else:
            text.translation = None
            text.translation_meta = {"status": "missing", "needs_retry": True}
    
    return page_texts
```

### 텍스트 ID 불일치 (text ID mismatch)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def validate_translation_ids(input_texts, translations):
    """번역 ID 검증"""
    input_ids = set([t.id for t in input_texts])
    translation_ids = set([t["id"] for t in translations])
    
    # 누락된 ID
    missing = input_ids - translation_ids
    if missing:
        warn(f"Missing translations for IDs: {missing}")
        # 누락된 것만 재번역
        missing_texts = [t for t in input_texts if t.id in missing]
        retry_translations = translate_batch(missing_texts)
        translations.extend(retry_translations)
    
    # 존재하지 않는 ID
    extra = translation_ids - input_ids
    if extra:
        warn(f"Unexpected translation IDs: {extra}")
        translations = [t for t in translations if t["id"] not in extra]
    
    return translations
```

### 순서 변경 감지 실패 (order change detection)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def verify_translation_order(original_texts, translations):
    """번역 순서 검증"""
    for i, (orig, trans) in enumerate(zip(original_texts, translations)):
        # LLM에게 원문 일부(처음 20자)를 응답에 포함하도록 요청
        original_snippet = orig.content[:20]
        if trans.get("original_snippet") != original_snippet:
            warn(f"Translation order mismatch at index {i}")
            # ID 기반 재정렬 시도
            translations = sort_by_id(translations, original_texts)
            break
    
    return translations
```

### 중복 매핑 (duplicate mapping)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def detect_duplicate_translations(translations):
    """중복 번역 감지"""
    translation_texts = [t["translation"] for t in translations]
    unique_count = len(set(translation_texts))
    total_count = len(translation_texts)
    
    duplicate_ratio = 1 - (unique_count / total_count)
    
    if duplicate_ratio > 0.3:  # 30% 이상 중복
        warn(f"High duplicate ratio: {duplicate_ratio:.1%}")
        return {"status": "suspicious", "ratio": duplicate_ratio}
    
    return {"status": "ok", "ratio": duplicate_ratio}
```

### 텍스트 타입 손실 (text type loss)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
class TranslatedText:
    def __init__(self, original_text):
        # 원본 정보
        self.id = original_text.id
        self.type = original_text.type  # dialogue, narration, SFX
        self.original = original_text.content
        self.bbox = original_text.bbox
        self.reading_order = original_text.reading_order
        self.balloon = original_text.balloon
        
        # 번역 정보
        self.translation = None
        
        # 메타데이터
        self.meta = {
            "quality_score": None,
            "model_used": None,
            "retry_count": 0,
            "timestamp": None
        }
```

### 위치 정보 손실 (position loss)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
def preserve_position_info(original_text, translation):
    """위치 정보 보존"""
    return {
        "id": original_text.id,
        "translation": translation,
        "position": {
            "bbox": original_text.bbox,  # {x, y, width, height}
            "rotation": original_text.rotation,
            "panel_id": original_text.panel_id
        }
    }
```

### 읽기 순서 손실 (reading order loss)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def preserve_reading_order(page_texts):
    """읽기 순서 유지"""
    for i, text in enumerate(sorted(page_texts, key=lambda t: (t.y, -t.x))):
        text.reading_order = i + 1
    
    # 번역 후에도 reading_order 유지
    return page_texts
```

### 다중 말풍선 매핑 (multi-balloon mapping)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
def split_multi_sentence_translation(original, translation):
    """다중 문장 번역 분할"""
    # 원문 문장 수
    original_sentences = original.split('。')
    original_count = len([s for s in original_sentences if s.strip()])
    
    # 번역 문장 수
    translation_sentences = translation.split('.')
    translation_count = len([s for s in translation_sentences if s.strip()])
    
    if original_count != translation_count:
        warn(f"Sentence count mismatch: {original_count} vs {translation_count}")
    
    # 각 문장을 별도 객체로
    return [{"sentence": s.strip(), "index": i} for i, s in enumerate(translation_sentences) if s.strip()]
```

### 빈 번역 처리 (empty translation)

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
def handle_empty_translation(original, translation):
    """빈 번역 처리"""
    if not translation or translation.strip() == "":
        # fallback: 원문 유지
        return {
            "translation": original,
            "status": "fallback",
            "reason": "Empty translation - using original"
        }
    return {"translation": translation, "status": "success"}
```

### 번역 후 메타데이터 (post-translation metadata)

**우선순위**: ⚪ LOW

**구현 코드**:

```python
def add_translation_metadata(translation, quality_score, model_name):
    """번역 후 메타데이터 추가"""
    translation.meta = {
        "quality_score": quality_score,  # 1~5
        "model_used": model_name,  # "gpt-4o", "gemini-flash"
        "retry_count": translation.get("retry_count", 0),
        "timestamp": datetime.now().isoformat(),
        "confidence": translation.get("confidence", None)
    }
    return translation
```

## STAGE ④ — 텍스트 제거 & 삽입

### 스크린톤 패턴 파괴 (CRITICAL)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
import cv2
import numpy as np
from numpy.fft import fft2, fftshift

# 1. 주변 영역에서 패턴 감지
surrounding = get_surrounding_region(inpaint_mask, padding=50)
f_transform = fft2(surrounding)
f_shift = fftshift(f_transform)
magnitude = np.abs(f_shift)

# 2. 주파수 도메인에서 피크 찾기 (패턴 주기)
peaks = find_frequency_peaks(magnitude)
pattern_tile = reconstruct_pattern_tile(peaks)

# 3. 패턴 타일을 inpaint 영역에 배치
inpaint_region = tile_pattern(pattern_tile, inpaint_mask.shape)

# 4. LaMa inpainting 적용 후 alpha blend
lama_result = lama.inpaint(image, inpaint_mask)
final = cv2.addWeighted(inpaint_region, 0.3, lama_result, 0.7, 0)
```

### 복잡한 배경 복원 실패 (인물 뒤, 건물)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
# 배경 복잡도 측정
edges = cv2.Canny(surrounding_region, 50, 150)
edge_density = np.sum(edges > 0) / edges.size

# 임계값 이상이면 SD inpainting 사용
if edge_density > 0.3:
    from diffusers import StableDiffusionInpaintPipeline
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "stabilityai/stable-diffusion-2-inpainting"
    )
    result = pipe(
        image=image,
        mask_image=mask,
        prompt="fill the area naturally with similar background",
        strength=0.8
    ).images[0]
else:
    result = lama.inpaint(image, mask)
```

### 텍스트 영역 경계의 halo effect

**우선순위**: 🟡 MEDIUM

**문제점**: inpaint된 영역과 원본 이미지의 경계에서 색상/밝기가 미묘하게 달라 '후광 효과' 생김.

**해결책**: inpaint 후 Poisson blending (cv2.seamlessClone) 적용해 경계 자연스럽게

**구현 코드**:

```python
# Poisson blending으로 경계 부드럽게
center = (inpaint_region.x + inpaint_region.width // 2,
          inpaint_region.y + inpaint_region.height // 2)
result = cv2.seamlessClone(
    inpainted_region,
    original_image,
    mask,
    center,
    cv2.NORMAL_CLONE
)
```

### 텍스트 영역 감지 오류로 일부만 제거

**우선순위**: 🔴 CRITICAL

**해결책**: 텍스트 영역 감지 시 bounding box를 의도적으로 확장 (padding +5~10px)

**구현 코드**:

```python
# bounding box 확장
padding = 10
expanded_bbox = {
    "x": bbox.x - padding,
    "y": bbox.y - padding,
    "width": bbox.width + 2 * padding,
    "height": bbox.height + 2 * padding
}

# morphological dilation으로 mask 팽창
kernel = np.ones((5, 5), np.uint8)
dilated_mask = cv2.dilate(text_mask, kernel, iterations=2)
```

### 반투명 텍스트 잔여 (앤티앨리어싱)

**우선순위**: 🟠 HIGH

**해결책**: inpaint mask를 생성할 때 alpha mask 사용. 반투명 영역도 포함하도록 임계값 낮춤

**구현 코드**:

```python
# 텍스트 영역을 Gaussian blur한 후 임계값 낮춤
blurred = cv2.GaussianBlur(text_region, (5, 5), 0)
_, alpha_mask = cv2.threshold(blurred, 0.3 * 255, 255, cv2.THRESH_BINARY)
```

### 말풍선 꼬리 손상

**우선순위**: 🟡 MEDIUM

**해결책**: 말풍선 경계 감지 후 꼬리는 convex hull 바깥 부분으로 판단, inpaint mask에서 제외

**구현 코드**:

```python
# GAP-A에서 이미 언급한 코드와 동일
hull = cv2.convexHull(contour)
tail_mask = cv2.subtract(contour_mask, hull_mask)
final_mask = cv2.bitwise_and(text_mask, cv2.bitwise_not(tail_mask))
```

### 텍스트가 말풍선 경계를 벗어남 (CRITICAL)

**우선순위**: 🔴 CRITICAL

**구현 코드**:

```python
from PIL import ImageDraw, ImageFont
import textwrap

balloon_width, balloon_height = calculate_balloon_size(contour)
font_size = 16
min_font_size = 10

while True:
    font = ImageFont.truetype("NotoSansKR.ttf", font_size)
    bbox = draw.textbbox((0, 0), translated_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    if text_width <= balloon_width and text_height <= balloon_height:
        break  # 들어감
    
    if font_size > min_font_size:
        font_size -= 1  # 폰트 축소
    else:
        # 최소 크기에 도달 → 줄바꿈 시도
        wrapped = textwrap.fill(translated_text, width=balloon_width // (font_size * 0.6))
        if calculate_height(wrapped) <= balloon_height:
            translated_text = wrapped
            break
        else:
            # 줄바꿈도 안 됨 → 수동 검증 큐
            manual_review_queue.append({"reason": "text overflow", "text": translated_text})
            break
```

### 텍스트 중심이 말풍선 중심과 안 맞음 (off-center)

**우선순위**: 🟠 HIGH

**해결책**: 말풍선의 무게중심(centroid) 계산 → 텍스트의 중심을 말풍선 중심에 맞춤

**구현 코드**:

```python
# 말풍선 무게중심 계산
M = cv2.moments(contour)
cx = int(M['m10'] / M['m00'])
cy = int(M['m01'] / M['m00'])

# 텍스트 렌더링 시 중심 정렬 (Pillow anchor='mm')
draw.text((cx, cy), translated_text, font=font, fill="black", anchor="mm")
```

### 세로 텍스트 배치 오류

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
if text_direction == "vertical":
    # 글자를 한 글자씩 수직으로 배치
    y_offset = 0
    for char in translated_text:
        draw.text((cx, cy + y_offset), char, font=font, fill="black", anchor="mm")
        y_offset += font.getbbox(char)[3] + 5  # 글자 높이 + 간격
else:
    # 가로쓰기
    draw.text((cx, cy), translated_text, font=font, fill="black", anchor="mm")
```

### 폰트 종류가 원본과 완전히 다름

**우선순위**: 🟠 HIGH

**해결책**: 텍스트 종류에 따라 폰트 매핑: 대화 → 둥근 고딕, SFX → Impact, 나레이션 → 세리프

**구현 코드**:

```python
FONT_MAPPING = {
    "dialogue": "NotoSansKR-Regular.ttf",
    "SFX": "Impact.ttf",
    "narration": "NotoSerifKR.ttf",
    "small_text": "NotoSansKR-Light.ttf"
}

font_path = FONT_MAPPING.get(text_type, "NotoSansKR-Regular.ttf")
font = ImageFont.truetype(font_path, font_size)
```

### 폰트 크기 자동 축소의 한계 (최소 크기)

**우선순위**: 🟠 HIGH

**구현 코드**:

```python
MIN_FONT_SIZE = 10

if font_size <= MIN_FONT_SIZE and text_still_overflows:
    # 텍스트를 LLM에게 요약 요청
    summarized = llm.summarize(translated_text, max_chars=balloon_width // MIN_FONT_SIZE)
    translated_text = summarized
```

### 한글 폰트의 자간·행간 문제

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
# Pillow는 기본적으로 자간 조정 미지원 → 수동으로 글자별 x 좌표 조정
def draw_text_with_spacing(draw, text, position, font, spacing=0):
    x, y = position
    for char in text:
        draw.text((x, y), char, font=font, fill="black")
        bbox = font.getbbox(char)
        x += (bbox[2] - bbox[0]) + spacing  # 글자 너비 + 자간
```

### 텍스트가 말풍선 테두리와 겹침

**우선순위**: 🟠 HIGH

**문제점**: 말풍선 내부 영역을 계산할 때 테두리 두께를 고려하지 않아, 텍스트가 테두리 선과 겹쳐 읽기 어려움.

**해결책**: 말풍선 경계 감지 후 내부 영역에서 마진 적용 (erode)

**구현 코드**:

```python
# 이미 GAP-A에서 다뤘음
kernel = np.ones((5, 5), np.uint8)
inner_balloon = cv2.erode(balloon_mask, kernel, iterations=1)
```

### 불규칙한 말풍선(구름형·폭발형) 처리 실패

**우선순위**: 🟡 MEDIUM

**해결책**: 불규칙한 말풍선은 convex hull로 근사. 또는 최대 내접 원 계산해 그 안에만 텍스트 배치

**구현 코드**:

```python
# convex hull로 단순화
hull = cv2.convexHull(irregular_contour)

# 또는 distance transform으로 최대 내접 원 찾기
dist_transform = cv2.distanceTransform(balloon_mask, cv2.DIST_L2, 5)
_, radius, _, center = cv2.minMaxLoc(dist_transform)
# center 안에만 텍스트 배치
```

### 겹치는 말풍선 처리 (연속 대화)

**우선순위**: ⚪ LOW

**해결책**: 말풍선 간 충돌 감지 → 겹치는 영역이 있으면 각 말풍선의 '배타적 영역'만 텍스트 배치 가능 영역으로

**구현 코드**:

```python
# 말풍선 contour끼리 AND 연산으로 겹치는 영역 계산
overlap = cv2.bitwise_and(balloon1_mask, balloon2_mask)
if np.sum(overlap) > 0:
    # 겹치는 영역은 '먼저 오는' 말풍선에 할당
    balloon1_exclusive = cv2.bitwise_and(balloon1_mask, cv2.bitwise_not(overlap))
```

### 텍스트 렌더링 시 앤티앨리어싱 불일치

**우선순위**: 🟡 MEDIUM

**구현 코드**:

```python
# 원본 텍스트가 픽셀아트 느낌이면 nearest-neighbor scaling으로 픽셀화
if original_style == "pixel_art":
    text_layer = cv2.resize(text_layer, text_layer.shape[:2][::-1], 
                            interpolation=cv2.INTER_NEAREST)
```

### 텍스트 그림자·외곽선 부재

**우선순위**: 🟡 MEDIUM

**해결책**: 원본 텍스트에 외곽선이 있으면, 새 텍스트에도 동일한 외곽선 추가 (PIL stroke_width)

**구현 코드**:

```python
# 외곽선
draw.text((x, y), text, font=font, fill="white", 
          stroke_width=2, stroke_fill="black")

# 그림자 (텍스트를 두 번 렌더링)
draw.text((x+2, y+2), text, font=font, fill="black")  # 그림자
draw.text((x, y), text, font=font, fill="white")  # 실제 텍스트
```

### 최종 이미지 압축 시 품질 저하

**우선순위**: ⚪ LOW

**해결책**: 텍스트가 있는 영역은 고품질로 압축 (JPEG quality 95+) 또는 PNG로 저장

**구현 코드**:

```python
from PIL import Image
image.save("output.jpg", format="JPEG", quality=95)
# 또는
image.save("output.webp", format="WEBP", quality=90)  # WebP는 손실 압축이지만 품질 좋음
```

## POST-PROCESSING

### 번역 누락 검증 (translation completeness)

**우선순위**: 🔴 CRITICAL

**ID**: `post-1`

**문제점**:
일부 텍스트가 번역 안 됨. Stage②에서 100개 감지 → Stage③에서 95개만 번역 → 5개 누락. 최종 출력에서 원본 텍스트 그대로 남음.

**해결책**:
입력 텍스트 개수 == 출력 이미지 텍스트 개수 검증. 누락 리스트 자동 생성 + 경고

**구현 코드**:

```python
def validate_translation_completeness(ocr_results, rendered_page):
    """번역 누락 검증"""
    original_count = len(ocr_results)
    
    # 렌더링된 페이지에서 텍스트 영역 감지
    rendered_text_regions = detect_text_regions(rendered_page)
    rendered_count = len(rendered_text_regions)
    
    if original_count != rendered_count:
        missing_count = original_count - rendered_count
        warn(f"번역 누락: {missing_count}개")
        
        # 누락된 텍스트 찾기
        missing_texts = find_missing_texts(ocr_results, rendered_text_regions)
        
        return {
            "status": "incomplete",
            "missing_count": missing_count,
            "missing_texts": missing_texts
        }
    
    return {"status": "complete"}
```

---

### 시각적 품질 검증 (visual quality check)

**우선순위**: 🟠 HIGH

**ID**: `post-2`

**문제점**:
텍스트가 말풍선 밖으로 튀어나감. 폰트가 너무 작음 (<8pt). 줄바꿈이 이상함. 자동 검증 없이 수동으로만 확인.

**해결책**:
자동 품질 검사 - bbox overflow 체크, 폰트 크기 < 8pt 경고, 텍스트 밀도 > 90% 경고

**구현 코드**:

```python
def validate_visual_quality(page_image, text_regions):
    """시각적 품질 자동 검증"""
    issues = []
    
    for region in text_regions:
        # 1. Bbox overflow
        if region.bbox.x < 0 or region.bbox.y < 0:
            issues.append({
                "type": "bbox_overflow",
                "region": region.id,
                "severity": "high"
            })
        
        # 2. 폰트 크기
        if region.font_size < 8:
            issues.append({
                "type": "font_too_small",
                "region": region.id,
                "font_size": region.font_size
            })
        
        # 3. 텍스트 밀도
        density = calculate_text_density(region)
        if density > 0.9:
            issues.append({
                "type": "text_density_high",
                "region": region.id,
                "density": density
            })
    
    return issues
```

---

### 번역 일관성 검증 (translation consistency)

**우선순위**: 🟠 HIGH

**ID**: `post-3`

**문제점**:
같은 페이지에서 캐릭터 이름 불일치. 1페이지: '다나카', 2페이지: '타나카', 3페이지: '다나카'. 독자 혼란.

**해결책**:
캐릭터 이름 딕셔너리 기반 검증. 불일치 감지 시 경고 + 수정 제안

**구현 코드**:

```python
def validate_name_consistency(pages, character_dict):
    """이름 일관성 검증"""
    inconsistencies = []
    
    for page in pages:
        for text in page.texts:
            if text.translation:
                # 딕셔너리에 있는 이름 찾기
                for original_name, standard_name in character_dict.items():
                    if original_name in text.original:
                        # 번역에 표준 이름이 있는지 확인
                        if standard_name not in text.translation:
                            # 다른 변형 찾기
                            found_variant = find_name_variant(text.translation, standard_name)
                            if found_variant:
                                inconsistencies.append({
                                    "page": page.number,
                                    "text_id": text.id,
                                    "expected": standard_name,
                                    "found": found_variant
                                })
    
    return inconsistencies
```

---

### 텍스트 가독성 검증 (readability check)

**우선순위**: 🟡 MEDIUM

**ID**: `post-4`

**문제점**:
배경과 텍스트 색상 대비 부족. 흰 배경에 흰 텍스트. WCAG 기준 (4.5:1) 미달.

**해결책**:
색상 대비 비율 계산. 부족하면 외곽선 추가 권장

**구현 코드**:

```python
def calculate_contrast_ratio(text_color, background_color):
    """WCAG 색상 대비 비율"""
    def relative_luminance(rgb):
        r, g, b = [x / 255.0 for x in rgb]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    l1 = relative_luminance(text_color)
    l2 = relative_luminance(background_color)
    
    lighter = max(l1, l2)
    darker = min(l1, l2)
    
    return (lighter + 0.05) / (darker + 0.05)

def validate_readability(text_regions):
    """가독성 검증"""
    issues = []
    
    for region in text_regions:
        contrast = calculate_contrast_ratio(region.text_color, region.background_color)
        
        if contrast < 4.5:  # WCAG AA 기준
            issues.append({
                "region": region.id,
                "contrast": contrast,
                "recommendation": "Add stroke or change color"
            })
    
    return issues
```

---

### 다양한 출력 형식 지원 (multiple formats)

**우선순위**: 🟠 HIGH

**ID**: `post-5`

**문제점**:
이미지만 출력. PDF/CBZ/EPUB 필요. 각 플랫폼마다 다른 형식 요구.

**해결책**:
Pillow → PDF (img2pdf), CBZ (zipfile), EPUB (ebooklib) 변환 지원

**구현 코드**:

```python
def export_to_format(pages, output_format="pdf"):
    """다양한 형식으로 출력"""
    if output_format == "pdf":
        import img2pdf
        
        image_files = [page.rendered_image_path for page in pages]
        pdf_bytes = img2pdf.convert(image_files)
        
        with open("output.pdf", "wb") as f:
            f.write(pdf_bytes)
    
    elif output_format == "cbz":
        import zipfile
        
        with zipfile.ZipFile("output.cbz", 'w') as z:
            for i, page in enumerate(pages):
                z.write(page.rendered_image_path, f"page_{i+1:03d}.png")
    
    elif output_format == "epub":
        from ebooklib import epub
        
        book = epub.EpubBook()
        for i, page in enumerate(pages):
            image = epub.EpubImage()
            image.file_name = f"page_{i+1}.png"
            image.content = open(page.rendered_image_path, 'rb').read()
            book.add_item(image)
        
        epub.write_epub('output.epub', book)
```

---

### 원본 메타데이터 보존 (metadata preservation)

**우선순위**: 🟡 MEDIUM

**ID**: `post-6`

**문제점**:
EXIF 데이터, 페이지 순서, 파일명 손실. 원본: '001_cover.jpg' → 출력: 'page_1.png'.

**해결책**:
원본 메타데이터 추출 → 출력 파일에 재적용

**구현 코드**:

```python
from PIL import Image
from PIL.ExifTags import TAGS

def preserve_metadata(original_image, translated_image):
    """메타데이터 보존"""
    # EXIF 추출
    exif = original_image.getexif()
    
    # 번역된 이미지에 적용
    if exif:
        translated_image.save("output.jpg", exif=exif)
    
    return translated_image

def preserve_filenames(original_files, translated_files):
    """파일명 구조 보존"""
    import os
    
    for orig_path, trans_path in zip(original_files, translated_files):
        # 원본 파일명 추출
        orig_name = os.path.basename(orig_path)
        name_without_ext = os.path.splitext(orig_name)[0]
        
        # 번역 파일명에 적용
        new_name = f"{name_without_ext}_translated.png"
        os.rename(trans_path, new_name)
```

---

### 압축 최적화 (compression optimization)

**우선순위**: 🟡 MEDIUM

**ID**: `post-7`

**문제점**:
PNG 출력 시 파일 크기 거대 (10MB/page). 웹 배포 시 로딩 느림.

**해결책**:
JPEG 품질 90% (시각적 차이 없음), PNG 최적화, WebP 옵션

**구현 코드**:

```python
def optimize_output(image, format="jpeg", quality=90):
    """출력 최적화"""
    if format == "jpeg":
        image.save("output.jpg", "JPEG", quality=quality, optimize=True)
    
    elif format == "png":
        # PNG 최적화 (pngquant 사용)
        import subprocess
        image.save("temp.png")
        subprocess.run(["pngquant", "--force", "--output", "output.png", "temp.png"])
    
    elif format == "webp":
        image.save("output.webp", "WEBP", quality=quality, method=6)
```

---

### Before/After 비교 이미지 (comparison)

**우선순위**: 🟠 HIGH

**ID**: `post-8`

**문제점**:
번역 품질 확인 어려움. 원본과 비교 못 함. 수동으로 이미지 2개 열어서 비교.

**해결책**:
좌우 비교 이미지 자동 생성. 슬라이더 UI로 전/후 비교

**구현 코드**:

```python
def generate_comparison_image(original, translated):
    """좌우 비교 이미지"""
    from PIL import Image, ImageDraw
    
    width = original.width + translated.width + 20
    height = max(original.height, translated.height)
    
    comparison = Image.new('RGB', (width, height), (255, 255, 255))
    
    # 원본 왼쪽
    comparison.paste(original, (0, 0))
    
    # 구분선
    draw = ImageDraw.Draw(comparison)
    draw.line([(original.width + 10, 0), 
               (original.width + 10, height)], 
              fill=(200, 200, 200), width=2)
    
    # 번역 오른쪽
    comparison.paste(translated, (original.width + 20, 0))
    
    # 라벨 추가
    draw.text((10, 10), "Original", fill=(0, 0, 0))
    draw.text((original.width + 30, 10), "Translated", fill=(0, 0, 0))
    
    return comparison
```

---

### 번역 통계 생성 (translation statistics)

**우선순위**: 🟡 MEDIUM

**ID**: `post-9`

**문제점**:
얼마나 번역했는지 모름. 성공률, 실패율, 평균 confidence 알 수 없음.

**해결책**:
페이지별 텍스트 개수, 번역률, 평균 confidence, 실패 케이스 통계 생성

**구현 코드**:

```python
def generate_translation_statistics(pages):
    """번역 통계"""
    stats = {
        "total_pages": len(pages),
        "total_texts": 0,
        "translated_texts": 0,
        "failed_texts": 0,
        "average_confidence": 0,
        "by_type": {
            "dialogue": {"count": 0, "success": 0},
            "narration": {"count": 0, "success": 0},
            "SFX": {"count": 0, "success": 0}
        }
    }
    
    confidences = []
    
    for page in pages:
        for text in page.texts:
            stats["total_texts"] += 1
            
            if text.translation:
                stats["translated_texts"] += 1
                stats["by_type"][text.type]["success"] += 1
                if text.translation_meta.get("confidence"):
                    confidences.append(text.translation_meta["confidence"])
            else:
                stats["failed_texts"] += 1
            
            stats["by_type"][text.type]["count"] += 1
    
    if confidences:
        stats["average_confidence"] = sum(confidences) / len(confidences)
    
    stats["translation_rate"] = stats["translated_texts"] / stats["total_texts"]
    
    return stats
```

---

### 상세 로그 파일 (detailed logging)

**우선순위**: 🟡 MEDIUM

**ID**: `post-10`

**문제점**:
오류 발생 시 디버깅 어려움. 어느 stage에서 실패했는지, 얼마나 걸렸는지 알 수 없음.

**해결책**:
JSON 로그 - 각 stage별 시간, 성공/실패, 오류 메시지, 입출력 데이터

**구현 코드**:

```python
import json
import time

class PipelineLogger:
    def __init__(self):
        self.logs = []
    
    def log_stage(self, stage_name, status, duration, details=None):
        """Stage 로그 기록"""
        log_entry = {
            "timestamp": time.time(),
            "stage": stage_name,
            "status": status,  # "success" or "failed"
            "duration_seconds": duration,
            "details": details or {}
        }
        self.logs.append(log_entry)
    
    def save_to_file(self, filepath="pipeline_log.json"):
        """로그 파일 저장"""
        with open(filepath, 'w') as f:
            json.dump(self.logs, f, indent=2)

# 사용 예
logger = PipelineLogger()

start_time = time.time()
try:
    result = run_ocr_stage(page)
    logger.log_stage("OCR", "success", time.time() - start_time, 
                      {"text_count": len(result)})
except Exception as e:
    logger.log_stage("OCR", "failed", time.time() - start_time,
                      {"error": str(e)})
```

---

### 수동 검증 큐 (manual review queue)

**우선순위**: 🟠 HIGH

**ID**: `post-11`

**문제점**:
자동 번역 실패 케이스 수동 처리 필요. 하지만 어떤 것이 실패했는지 찾기 어려움.

**해결책**:
실패 케이스를 별도 폴더에 저장. 웹 UI로 수동 수정 후 재처리

**구현 코드**:

```python
import os
import shutil

class ManualReviewQueue:
    def __init__(self, queue_dir="./manual_review"):
        self.queue_dir = queue_dir
        os.makedirs(queue_dir, exist_ok=True)
        self.queue = []
    
    def add_to_queue(self, page_id, reason, image, metadata):
        """큐에 추가"""
        item = {
            "page_id": page_id,
            "reason": reason,
            "timestamp": time.time(),
            "metadata": metadata
        }
        
        # 이미지 저장
        image_path = os.path.join(self.queue_dir, f"{page_id}_{reason}.png")
        image.save(image_path)
        item["image_path"] = image_path
        
        self.queue.append(item)
    
    def export_queue(self):
        """큐 내보내기"""
        with open(os.path.join(self.queue_dir, "queue.json"), 'w') as f:
            json.dump(self.queue, f, indent=2)

# 사용 예
review_queue = ManualReviewQueue()

if ocr_confidence < 0.4:
    review_queue.add_to_queue(page.id, "low_ocr_confidence", 
                               page.image, {"confidence": ocr_confidence})
```

---

### 재처리 파이프라인 (re-processing pipeline)

**우선순위**: ⚪ LOW

**ID**: `post-12`

**문제점**:
일부만 수정하고 싶은데 전체 재실행 필요. 시간 낭비.

**해결책**:
캐시 시스템. Stage별 중간 결과 저장. 특정 stage부터 재시작 가능

**구현 코드**:

```python
import pickle

class CachedPipeline:
    def __init__(self, cache_dir="./cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def save_cache(self, stage_num, data):
        """중간 결과 캐시"""
        cache_file = os.path.join(self.cache_dir, f"stage_{stage_num}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    
    def load_cache(self, stage_num):
        """캐시 로드"""
        cache_file = os.path.join(self.cache_dir, f"stage_{stage_num}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def run_from_stage(self, start_stage, input_data):
        """특정 stage부터 재시작"""
        # 이전 stage 결과 로드
        if start_stage > 1:
            cached_data = self.load_cache(start_stage - 1)
            if cached_data:
                print(f"Loaded cache from stage {start_stage - 1}")
                input_data = cached_data
        
        # start_stage부터 실행
        for stage_num in range(start_stage, 10):
            result = self.run_stage(stage_num, input_data)
            self.save_cache(stage_num, result)
            input_data = result
        
        return input_data
```

---

