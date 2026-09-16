import cv2
import numpy as np
from pathlib import Path

image_path = Path(__file__).with_name('cat.jpg')
img = cv2.imread(str(image_path))
if img is None:
	raise FileNotFoundError(f'無法讀取影像檔案：{image_path}')
print(img.shape)

kernel = np.ones((5, 5), np.float32) / 25

dst = cv2.filter2D(img, -1, kernel)

# 均值濾波
dst = cv2.blur(img, (5, 5))

# 高斯濾波，針對高斯雜訊
dst = cv2.GaussianBlur(img, (5, 5), sigmaX=1)

# 中值濾波，針對胡椒雜訊
dst = cv2.medianBlur(img, 5)

# 雙邊濾波
dst = cv2.bilateralFilter(img, 7, 20, 50)

# Sobel
# y方向的邊緣
dst_y = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=5)
# x方向的邊緣
dst_x = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=5)
dst = dst_x + dst_y
dst = cv2.add(dst_x, dst_y)

# Scharr
dst_y = cv2.Scharr(img, cv2.CV_64F, 1, 0)
dst_x = cv2.Scharr(img, cv2.CV_64F, 0, 1)
dst = cv2.add(dst_x, dst_y)

# 拉普拉斯 可以同時計算兩個方向的梯度
dst = cv2.Laplacian(img, cv2.CV_64F, ksize=5)

# Canny 邊緣檢測終極大法
dst = cv2.Canny(img, 100, 200)
print(dst.shape)

cv2.imshow('dst', dst)
cv2.imshow('img', img)
cv2.waitKey(0)

