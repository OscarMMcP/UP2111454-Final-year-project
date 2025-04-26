import sys
import os
import math
import time
import numpy as np
import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QToolBar, QDockWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QListWidget, QColorDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QDialog, 
    QLabel, QSlider, QStackedWidget, QTabWidget, QComboBox, QMessageBox,
QGraphicsRectItem, QGraphicsPathItem
)
from PyQt6.QtGui import (QAction, QActionGroup, QPixmap, QMouseEvent, QPen, QPainter, QFont, QColor, QImage, QBrush, QPainterPath,
    QPolygonF, QTransform
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF, QTimer
from PIL import Image, ImageQt, ImageDraw, ImageChops
from blend_modes import soft_light, lighten_only, dodge, addition, darken_only, multiply, hard_light, difference, subtract, grain_extract, grain_merge, divide, overlay, normal

BLEND_MODE_MAP = {
    "normal": normal,
    "multiply": multiply,
    "overlay": overlay,
    "darken": darken_only,
    "lighten": lighten_only,
    "difference": difference,
    "addition": addition,
    "subtract": subtract,
    "divide": divide,
    "hard_light": hard_light,
    "soft_light": soft_light,
    "dodge": dodge,
    "grain_extract": grain_extract,
    "grain_merge": grain_merge,
}

# --- Startup Dialog ---
class StartupDialog(QDialog):
    """
    Create startup dialogue asking for the size or an image
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Canvas Size")
        self.image_path = None

        layout = QVBoxLayout(self)

        instructions = QLabel("Enter canvas width and height (in pixels), or open an image to use its size:")
        layout.addWidget(instructions)

        sizeLayout = QHBoxLayout()
        self.widthEdit = QLineEdit("2000")
        self.widthEdit.setPlaceholderText("Width (e.g., 2000)")
        self.heightEdit = QLineEdit("2000")
        self.heightEdit.setPlaceholderText("Height (e.g., 2000)")
        sizeLayout.addWidget(self.widthEdit)
        sizeLayout.addWidget(self.heightEdit)
        layout.addLayout(sizeLayout)

        buttonLayout = QHBoxLayout()
        self.confirmButton = QPushButton("Confirm")
        self.confirmButton.clicked.connect(self.accept)
        self.openButton = QPushButton("Open")
        self.openButton.clicked.connect(self.openImage)
        buttonLayout.addWidget(self.confirmButton)
        buttonLayout.addWidget(self.openButton)
        layout.addLayout(buttonLayout)

    def openImage(self):
        """
        Opens a file dialog to allow the user to open an image. 
        Sets the canvas size based on the image dimensions.
        """
        # options = QFileDialog.Option.DontUseNativeDialog
        FileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if FileName:
            self.image_path = FileName  # Ensure it's a valid file path
            try:
                with Image.open(self.image_path) as img:
                    width, height = img.size
                self.widthEdit.setText(str(width))
                self.heightEdit.setText(str(height))
                self.accept()  # Accept the dialog
                print("Loading image from:", FileName)
            except Exception as e:
                print(f"Error loading image: {e}")
                self.accept()  # Accept the dialog even if there was an error

    def getData(self):
        """
        Returns the selected data (custom dimensions or image path).
        """
        if self.image_path:
            return ("image", self.image_path)
        try:
            width = int(self.widthEdit.text())
            height = int(self.heightEdit.text())
        except ValueError:
            width, height = 2000, 2000
        return ("custom", width, height)


def tickSpacing(zoom):
    """
    Global function for grid and ruler spacing
    Allows for Grid and ruler to change depending on zoom
    """
    if zoom >= 16:
        return 1
    elif zoom >= 8:
        return 5
    elif zoom >= 4:
        return 10
    elif zoom >= 2:
        return 20
    elif zoom >= 1:
        return 50
    elif zoom >= 0.5:
        return 100
    elif zoom >= 0.25:
        return 200
    else:
        return 500

# --- Custom Scene for Grid and Rulers ---
class CustomScene(QGraphicsScene):
    """
    Custom Scene which enables the zooming,
    as well as rulers
    """
    def __init__(self, gridEnabled=False, rulerEnabled=False, parent=None):
        super().__init__(parent)
        self.gridEnabled = gridEnabled
        self.rulerEnabled = rulerEnabled
        self.zoomScale = 1.0

    def update_zoom(self, zoomPercentage):
        self.zoomScale = zoomPercentage / 100.0

    def drawForeground(self, painter: QPainter, rect: QRectF):
        spacing = tickSpacing(self.zoomScale)

        # Draw Grid
        if self.gridEnabled and self.zoomScale >= 0.1:
            penMinorSpacing = QPen(Qt.GlobalColor.lightGray)
            penMajorSpacing = QPen(Qt.GlobalColor.gray)
            penMinorSpacing.setWidth(0)
            penMinorSpacing.setCosmetic(True)
            penMajorSpacing.setWidth(0)
            penMajorSpacing.setCosmetic(True)

            painter.setPen(penMinorSpacing)
            left = math.floor(rect.left() / spacing) * spacing
            top = math.floor(rect.top() / spacing) * spacing

            x = left
            while x < rect.right():
                pen = penMajorSpacing if spacing <= 10 or int(x) % (spacing * 5) == 0 else penMinorSpacing
                painter.setPen(pen)
                painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
                x += spacing

            y = top
            while y < rect.bottom():
                pen = penMajorSpacing if spacing <= 10 or int(y) % (spacing * 5) == 0 else penMinorSpacing
                painter.setPen(pen)
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
                y += spacing

        # Draw Ruler
        if self.rulerEnabled:
            rulerTick = QPen(Qt.GlobalColor.darkGray)
            rulerTick.setWidth(0)
            rulerTick.setCosmetic(True)
            painter.setPen(rulerTick)
            rulerNum = self.zoomScale >= 0.3

            font = QFont("Arial", int(8 / self.zoomScale))
            painter.setFont(font)

            step = spacing
            start_x = math.floor(rect.left() / step) * step
            x = start_x
            while x < rect.right():
                height = 10 if spacing <= 10 or int(x) % (spacing * 5) == 0 else 6 if int(x) % spacing == 0 else 3
                painter.drawLine(QLineF(x, rect.top(), x, rect.top() + height))
                if rulerNum and int(x) % (spacing * 5) == 0:
                    painter.drawText(QPointF(x + 2, rect.top() + 10), str(int(x)))
                x += step

            start_y = math.floor(rect.top() / step) * step
            y = start_y
            while y < rect.bottom():
                height = 10 if spacing <= 10 or int(y) % (spacing * 5) == 0 else 6 if int(y) % spacing == 0 else 3
                painter.drawLine(QLineF(rect.left(), y, rect.left() + height, y))
                if rulerNum and int(y) % (spacing * 5) == 0:
                    painter.drawText(QPointF(rect.left() + 12, y + 4), str(int(y)))
                y += step

# --- Layer Class ---
class Layer:
    """
    Represents a single layer on the canvas
    """
    def __init__(self, name, pil_image, layerOpacity=255, blendMode =  "normal"):
        self.name = name
        self.pil_image = pil_image
        self.opacity = layerOpacity
        self.blendMode = blendMode
        self.qt_pixmap = QPixmap.fromImage(ImageQt.ImageQt(pil_image))
        self.graphicsItem = None  # To be set when added to the canvas
        self.clippingMaskEnabled = False

    def updatePixmap(self, below=None):
        base = self.pil_image

        topImage = base.convert("RGBA")
        below = below.convert("RGBA") if below else None

        topArray = np.array(topImage).astype(np.float32)

        # Apply opacity to alpha channel before blending
        topArray[..., 3] *= self.opacity / 255.0

        if below is not None:
            baseArray = np.array(below).astype(np.float32)

            if topArray.shape[2] != 4 or baseArray.shape[2] != 4:
                raise ValueError("Both layers must be RGBA format.")

            blendFunction = BLEND_MODE_MAP.get(self.blend_mode, normal)
            blendedArray = blendFunction(topArray, baseArray, 1.0)
            blendedImage = Image.fromarray(np.uint8(np.clip(blendedArray, 0, 255)), mode="RGBA")
        else:
            blendedImage = Image.fromarray(np.uint8(np.clip(topArray, 0, 255)), mode="RGBA")

        self.qt_pixmap = QPixmap.fromImage(ImageQt.ImageQt(blendedImage))

        if self.graphicsItem:
            self.graphicsItem.setPixmap(self.qt_pixmap)
        else:
            self.graphicsItem = QGraphicsPixmapItem(self.qt_pixmap)

class Canvas(QGraphicsView):
    """
    The main drawing area of the program
    Includes all tool logic within the canvas
    """
    def __init__(self, sceneWidth=2000, sceneHeight=2000, gridEnabled=False, rulerEnabled=False, parent=None):
        super().__init__(parent)
        """
        Canvas and tools setup
        """
        self.sceneWidth = sceneWidth
        self.sceneHeight = sceneHeight
        self.gridEnabled = gridEnabled
        self.rulerEnabled = rulerEnabled

        self.customScene = CustomScene(gridEnabled=gridEnabled, rulerEnabled=rulerEnabled)

        # Dynamically calculate scene rect based on canvas size
        self.customScene.setSceneRect(0, 0, self.sceneWidth, self.sceneWidth)

        self.setScene(self.customScene)

        self.layers = []
        self.selectedLayerNames = set()
        self.currentLayer = None

        self.currentTool = "paintbrush"
        self.penColour = (0, 0, 0, 255)
        self.penWidth = 50
        self.eraserWidth = 50
        self.brushSpacing = 1
        self.eraserSpacing = 1
        self.brushImage = None
        self.eraserImage = None
        self.brushMask = None
        self.eraserMask = None
        self.brushOpacity = 255
        self.eraserOpacity = 255
        self.pencilWidth = 3
        self.pencilOpacity = 255
        self.pencilSpacing = 1
        self.pencilMode = "draw" 
        self.pencilMask = None
        self.pencilImage = None

        self.drawing = False
        self.lastPoint = None
        self.lastStampPos = None
        self.strokeBuffer = None

        self.zoomFactor = 1.0
        self.currentZoom = 100
        self.moveLastMousePos = None
        self.currentScrollPos = QPointF(0, 0)
        
        self.selectionTool = "marquee"
        self.selectionRectangle = None
        self.selectionItem = None 
        self.selectionMask = None
        self.selectionStartPoint = None
        self.isSelectionDragging = False
        self.selectionLineDashes = 0
        self.selectionLineAnimation = QTimer()
        self.selectionLineAnimation.setInterval(100)
        self.selectionLineAnimation.timeout.connect(self.animateSelection)
        self.selectionLineAnimation.start()
        self.lassoPoints = []
        self.lassoPathItem = None
        
        self.isSelectionMoving = False
        self.selectionStartPoint = None
        self.selectionMovedBackup = None
        self.selectionMovedMask = None
        self.selectionDragOffset = (0, 0)
        self.transformationHandles = []
        self.currentHandle = None
        self.transformBoundingBox = None
        self.transformOriginal = None
        self.transformationMode = None
        self.rotationBackup = None
        self.pointOfRotation = None
        self.rotationStartAngle = None

        self.undoStack = []
        self.redoStack = []

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self.shapeStartPoint = None
        self.shapePreviewBuffer = None
        
        self.loadBrushImage("brushes/01.png")
        self.loadEraserImage("brushes/01.png")
        self.loadPencilImage("brushes/01.png")

        QTimer.singleShot(0, self.autoZoom)

    def loadBrushImage(self, path):
        """
        Loads the brush
        """
        if not os.path.exists(path):
            print(f"Brush image not found: {path}")
            return
        baseImg = Image.open(path).convert("L")
        mask = mask = baseImg.convert("L")
        self.brushMask = mask
        self.updateBrush()

        
    def updateBrush(self):
        """
        Updates brush based off of inputs
        """
        if self.brushMask is None:
            return

        scaledSize = (self.penWidth, self.penWidth)
        resizedMask = self.brushMask.resize(scaledSize, Image.LANCZOS)


        alpha = resizedMask.point(lambda p: int(p * (self.brushOpacity / 255)))

        coloured = Image.new("RGBA", resizedMask.size, self.penColour[:3] + (0,))
        coloured.putalpha(alpha)

        self.brushImage = coloured

    def loadEraserImage(self, path):
        """
        Load the eraser image
        """
        if not os.path.exists(path):
            print(f"Eraser brush image not found: {path}")
            return
        baseImg = Image.open(path).convert("L")
        mask = mask = baseImg.convert("L")
        alpha = mask
        eraserImg = Image.new("RGBA", baseImg.size, (0, 0, 0, 0))
        eraserImg.putalpha(alpha)
        self.eraserMask = mask
        self.eraserImage = eraserImg
        self.updateEraser()

    def updateEraser(self):
        """
        Updates the eraaser based off its inputs
        """
        if self.eraserMask is None:
            return

        scaledSize = (self.eraserWidth, self.eraserWidth)
        resizedMask = self.eraserMask.resize(scaledSize, Image.LANCZOS)

        # Apply opacity scaling to alpha
        alpha = resizedMask.point(lambda p: int(p * (self.eraserOpacity / 255)))

        # Transparent RGBA with soft alpha
        eraserImg = Image.new("RGBA", resizedMask.size, (0, 0, 0, 0))
        eraserImg.putalpha(alpha)

        self.eraserImage = eraserImg

    def loadPencilImage(self, path):
        if not os.path.exists(path):
            print(f"Pencil brush image not found: {path}")
            return
        mask = Image.open(path).convert("L")
        self.pencilMask = mask
        self.updatePencil()

    def updatePencil(self):
        if self.pencilMask is None:
            return

        size = (self.pencilWidth, self.pencilWidth)
        resized = self.pencilMask.resize(size, Image.NEAREST)
        alpha = resized.point(lambda p: int(p * (self.pencilOpacity / 255)))
        
        if self.pencilMode == "erase":
            img = Image.new("RGBA", resized.size, (0, 0, 0, 0))
            img.putalpha(alpha)
        else:
            img = Image.new("RGBA", resized.size, self.penColour[:3] + (0,))
            img.putalpha(alpha)

        self.pencilImage = img

    def addLayer(self, layer):
        """
        adds a layer to the canvas
        """
        self.layers.append(layer)
        item = QGraphicsPixmapItem(layer.qt_pixmap)
        item.setZValue(len(self.layers))
        self.customScene.addItem(item)
        layer.graphicsItem = item

        if len(self.layers) == 1:
            self.centerOn(item)
            self.currentScrollPos = self.mapToScene(self.viewport().rect().center())

    def updateLayerOrder(self):
        self.customScene.clear()

        if not self.layers:
            return

        canvasWidth = self.sceneWidth
        canvasHeight = self.sceneHeight

        # Start with a blank canvas (transparent base)
        baseImage = Image.new("RGBA", (canvasWidth, canvasHeight), (0, 0, 0, 0))

        for layer in self.layers:
            # Always use raw image data
            if layer.pil_image.mode != "RGBA":
                layer.pil_image = layer.pil_image.convert("RGBA")

            # Blend onto baseImage using blend_modes
            topLayer = np.array(layer.pil_image).astype(np.float32)
            baseLayer = np.array(baseImage).astype(np.float32)

            blendFunction = BLEND_MODE_MAP.get(layer.blendMode, normal)
            blendedLayers = blendFunction(topLayer, baseLayer, layer.opacity / 255.0)
            blendedLayers = np.clip(blendedLayers, 0, 255).astype(np.uint8)
            baseImage = Image.fromarray(blendedLayers, mode="RGBA")

            # Update visual layer from composite
            layer.qt_pixmap = QPixmap.fromImage(ImageQt.ImageQt(baseImage))
            layer.graphicsItem = QGraphicsPixmapItem(layer.qt_pixmap)
            self.customScene.addItem(layer.graphicsItem)

    def wheelEvent(self, event):
        """
        Smooths vertical scrolling
        """
        step = event.angleDelta().y() / 3  # smooth scroll

        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.currentScrollPos -= QPointF(step, 0)
        else:
            self.currentScrollPos -= QPointF(0, step)

        self.centerOn(self.currentScrollPos)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """
        All initial mouse events
        """
        if self.currentTool == "move" and event.button() == Qt.MouseButton.LeftButton:
            self.moveLastMousePos = event.pos()
            event.accept()
            return

        if self.currentTool in ("paintbrush", "eraser", "pencil") and event.button() == Qt.MouseButton.LeftButton and self.currentLayer:
            self.pushUndo("Paint/Eraser Stroke")
            self.drawing = True
            scenePos = self.mapToScene(event.position().toPoint())
            x, y = int(scenePos.x()), int(scenePos.y())
            self.lastPoint = (x, y)
            self.lastStampPos = (x, y)
            self.stampBrush(x, y)
            event.accept()
            return
        if self.currentTool == "fill" and event.button() == Qt.MouseButton.LeftButton and self.currentLayer:
            self.pushUndo("Fill tool")
            scenePos = self.mapToScene(event.position().toPoint())
            x, y = int(scenePos.x()), int(scenePos.y())
            self.floodFill(x, y, self.penColour)
            self.currentLayer.updatePixmap()
            event.accept()
            return
        
        if self.currentTool == "shape" and event.button() == Qt.MouseButton.LeftButton and self.currentLayer:
            self.pushUndo("Shape Tool")
            scenePos = self.mapToScene(event.position().toPoint())
            self.shapeStartPoint = (int(scenePos.x()), int(scenePos.y()))
            self.shapePreviewBuffer = self.currentLayer.pil_image.copy()
            event.accept()
            return
        
        if self.currentTool == "selection":
            self.isSelectionDragging = True

            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                self.selectionMode = "add"
            elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                self.selectionMode = "subtract"
            else:
                self.selectionMode = "replace"

            pos = self.mapToScene(event.position().toPoint())

            if self.selectionTool == "marquee":
                self.selectionStartPoint = pos
                self.selectionRectangle = QRectF(pos, pos)

                if self.selectionItem:
                    self.customScene.removeItem(self.selectionItem)

                pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)

                self.selectionItem = QGraphicsRectItem(self.selectionRectangle)
                self.selectionItem.setPen(pen)
                self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                self.selectionItem.setZValue(1000)
                self.customScene.addItem(self.selectionItem)

            elif self.selectionTool == "lasso":
                self.lassoPoints = [pos]

                if self.lassoPathItem:
                    self.customScene.removeItem(self.lassoPathItem)
                    self.lassoPathItem = None

            return
        scenePos = self.mapToScene(event.position().toPoint())

        if self.currentTool == "transform":
            clickedHandle = None
            for i, handle in enumerate(self.transformationHandles):
                if handle.sceneBoundingRect().contains(scenePos):
                    clickedHandle = i
                    break

            if clickedHandle is not None:
                print(f"[PRESS] Transform handle {clickedHandle} clicked")
                self.currentHandle = clickedHandle
                self.transformOriginal = self.currentLayer.pil_image.copy()
                self.transformBoundingBox = self.selectionMask.getbbox() if self.selectionMask else self.currentLayer.pil_image.getbbox()
                self.dragStartPosition = scenePos
                self.transformationMode = "selection" if self.selectionMask else "layer"

                if clickedHandle == 8:
                    cx = (self.transformBoundingBox[0] + self.transformBoundingBox[2]) / 2
                    cy = (self.transformBoundingBox[1] + self.transformBoundingBox[3]) / 2
                    self.pointOfRotation = QPointF(cx, cy)
                    self.rotationStartAngle = math.atan2(scenePos.y() - cy, scenePos.x() - cx)
                    self.rotationBackup = self.currentLayer.pil_image.copy()
                return

            # No handle clicked — check for translation
            if self.selectionMask:
                try:
                    if self.selectionMask.getpixel((int(scenePos.x()), int(scenePos.y()))) > 0:
                        print("[PRESS] Inside selection — start translation")
                        self.selectionStartPoint = (int(scenePos.x()), int(scenePos.y()))
                        self.isSelectionMoving = True
                        self.selectionMovedBackup = self.currentLayer.pil_image.copy()
                        return
                except Exception as e:
                    print("[PRESS] Selection check error:", e)

        super().mouseMoveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Mouse movement
        """
        if self.currentTool == "move" and event.buttons() == Qt.MouseButton.LeftButton and self.moveLastMousePos:
            oldScene = self.mapToScene(self.moveLastMousePos)
            newScene = self.mapToScene(event.pos())
            delta = oldScene - newScene  # move camera opposite to drag
            self.currentScrollPos += delta
            self.centerOn(self.currentScrollPos)
            self.moveLastMousePos = event.pos()
            event.accept()
            return

        if self.currentTool in ("paintbrush", "eraser", "pencil") and self.drawing and self.currentLayer:
            scenePos = self.mapToScene(event.position().toPoint())
            x, y = int(scenePos.x()), int(scenePos.y())
            current = (x, y)
            if self.lastStampPos:
                dx = current[0] - self.lastStampPos[0]
                dy = current[1] - self.lastStampPos[1]
                distance = math.hypot(dx, dy)
                spacing = self.brushSpacing if self.currentTool == 'paintbrush' else self.eraserSpacing
                if distance >= spacing:
                    steps = int(distance / spacing)
                    for i in range(steps):
                        t = i / steps
                        ix = int(self.lastStampPos[0] + dx * t)
                        iy = int(self.lastStampPos[1] + dy * t)
                        self.stampBrush(ix, iy)
                    self.lastStampPos = current
            event.accept()
            return

        if self.currentTool == "shape" and self.shapeStartPoint and self.currentLayer:
            scenePos = self.mapToScene(event.position().toPoint())
            endPoint = (int(scenePos.x()), int(scenePos.y()))
            self.currentLayer.pil_image = self.shapePreviewBuffer.copy()

            draw = ImageDraw.Draw(self.currentLayer.pil_image, "RGBA")
            shape = self.getShapeType()
            width = self.getShapeWidth()
            colour = self.penColour

            if shape == "Line":
                draw.line([self.shapeStartPoint, endPoint], fill=colour, width=width)
            elif shape == "Rectangle":
                rect = self.normaliseRect(self.shapeStartPoint, endPoint)
                draw.rectangle(rect, outline=colour, width=width)
            elif shape == "Circle":
                rect = self.normaliseRect(self.shapeStartPoint, endPoint)
                draw.ellipse(rect, outline=colour, width=width)

            self.currentLayer.updatePixmap()
            event.accept()
            return
        if self.currentTool == "selection" and self.isSelectionDragging:
            pos = self.mapToScene(event.position().toPoint())

            if self.selectionTool == "marquee" and self.selectionStartPoint:
                self.selectionRectangle = QRectF(self.selectionStartPoint, pos).normalized()

                if self.selectionItem:
                    self.customScene.removeItem(self.selectionItem)

                pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)

                self.selectionItem = QGraphicsRectItem(self.selectionRectangle)
                self.selectionItem.setPen(pen)
                self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                self.selectionItem.setZValue(1000)
                self.customScene.addItem(self.selectionItem)

            elif self.selectionTool == "lasso":
                self.lassoPoints.append(pos)

                if self.lassoPathItem:
                    self.customScene.removeItem(self.lassoPathItem)

                path = QPainterPath()
                path.moveTo(self.lassoPoints[0])
                for pt in self.lassoPoints[1:]:
                    path.lineTo(pt)

                self.lassoPathItem = QGraphicsPathItem(path)
                pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                self.lassoPathItem.setPen(pen)
                self.lassoPathItem.setZValue(1000)
                self.customScene.addItem(self.lassoPathItem)

            return
            
        scenePos = self.mapToScene(event.position().toPoint())

        if self.currentTool == "transform":
            if self.isSelectionMoving:
                dx = int(scenePos.x()) - self.selectionStartPoint[0]
                dy = int(scenePos.y()) - self.selectionStartPoint[1]
                print(f"[MOVE] Translating selection by ({dx}, {dy})")

                source = self.selectionMovedBackup
                mask = self.selectionMask
                self.currentLayer.pil_image = source.copy()

                region = Image.composite(source, Image.new("RGBA", source.size, (0, 0, 0, 0)), mask)
                cleared = Image.composite(Image.new("RGBA", source.size, (0, 0, 0, 0)), source, mask)
                self.currentLayer.pil_image = cleared
                self.currentLayer.pil_image.paste(region, (dx, dy), region)

                newMask = Image.new("L", mask.size, 0)
                newMask.paste(mask, (dx, dy))
                self.selectionDragOffset = (dx, dy)
                self.selectionMovedMask = newMask

                if self.selectionItem:
                    self.selectionItem.setPos(dx, dy)

                self.currentLayer.updatePixmap()
                self.viewport().update()
                return
            
            if self.currentHandle == 8 and self.pointOfRotation and self.rotationBackup:
                print("[MOVE] Rotating selection/layer")

                pos = self.mapToScene(event.position().toPoint())
                centreX, centreY = self.pointOfRotation.x(), self.pointOfRotation.y()

                currentAngle = math.atan2(pos.y() - centreY, pos.x() - centreX)
                angleDelta = math.degrees(currentAngle - self.rotationStartAngle)

                source = self.rotationBackup
                x0, y0, x1, y1 = self.transformBoundingBox
                region = source.crop((x0, y0, x1, y1))

                if self.transformationMode == "selection" and self.selectionMask:
                    mask = self.selectionMask
                    maskCrop = mask.crop((x0, y0, x1, y1))

                    cleared = Image.composite(Image.new("RGBA", source.size, (0, 0, 0, 0)), source, mask)

                    rotatedRegion = region.rotate(-angleDelta, resample=Image.NEAREST, center=(region.width // 2, region.height // 2), expand=True)
                    rotatedMask = maskCrop.rotate(-angleDelta, resample=Image.Resampling.NEAREST, center=(maskCrop.width // 2, maskCrop.height // 2), expand=True)

                    newWidth, newHeight = rotatedRegion.size
                    pasteX = int(centreX - newWidth // 2)
                    pasteY = int(centreY - newHeight // 2)

                    result = cleared.copy()
                    result.paste(rotatedRegion, (pasteX, pasteY), rotatedMask)
                    self.currentLayer.pil_image = result

                    # Store for release
                    self.rotatedMaskPreview = Image.new("L", mask.size, 0)
                    self.rotatedMaskPreview.paste(rotatedMask, (pasteX, pasteY))
                    self.rotatedPreview = result

                    # Rotate selectionItem visually
                    if self.selectionItem:
                        transform = QTransform()
                        transform.translate(centreX, centreY)
                        transform.rotate(angleDelta)
                        transform.translate(-centreX, -centreY)
                        self.selectionItem.setTransform(transform)

                    # Update handles
                    if self.transformationHandles:
                        handles = [
                            QPointF(x0, y0),  # 0 top-left
                            QPointF(x1, y0),  # 1 top-right
                            QPointF(x1, y1),  # 2 bottom-right
                            QPointF(x0, y1),  # 3 bottom-left
                            QPointF((x0 + x1) / 2, y0),         # 4 top-center
                            QPointF(x1, (y0 + y1) / 2),         # 5 right-center
                            QPointF((x0 + x1) / 2, y1),         # 6 bottom-center
                            QPointF(x0, (y0 + y1) / 2),         # 7 left-center
                            QPointF((x0 + x1) / 2, y0 - 30),    # 8 rotation handle
                        ]

                        # Apply rotation to each point
                        for i, handle in enumerate(self.transformationHandles):
                            pt = handles[i]
                            vec = pt - self.pointOfRotation
                            radians = math.radians(angleDelta)
                            rotated = QPointF(
                                vec.x() * math.cos(radians) - vec.y() * math.sin(radians),
                                vec.x() * math.sin(radians) + vec.y() * math.cos(radians)
                            ) + self.pointOfRotation
                            handle.setPos(rotated)

                else:
                    # Rotate full image (no selection)
                    rotated = source.rotate(-angleDelta, center=(centreX, centreY), resample=Image.BICUBIC)
                    self.currentLayer.pil_image = rotated
                    self.rotatedPreview = rotated
                    self.rotatedMaskPreview = None

                self.currentLayer.updatePixmap()
                self.viewport().update()
                return
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Mouse button released
        """
        if self.currentTool == "move" and event.button() == Qt.MouseButton.LeftButton:
            self.moveLastMousePos = None
            event.accept()
            return

        if self.currentTool in ("paintbrush", "eraser", "pencil") and self.drawing and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            if self.currentLayer:
                self.currentLayer.updatePixmap()
            self.lastPoint = None
            self.lastStampPos = None
            event.accept()
            return
        if self.currentTool == "shape" and event.button() == Qt.MouseButton.LeftButton and self.shapeStartPoint:
            self.shapeStartPoint = None
            self.shapePreviewBuffer = None
            self.currentLayer.updatePixmap()
            event.accept()
            return

        if self.currentTool == "selection":
            self.isSelectionDragging = False
            modifiers = event.modifiers()

            if self.selectionTool == "marquee":
                self.finaliseMarqueeSelection(modifiers)
                self.selectionStartPoint = None

            elif self.selectionTool == "lasso":
                if len(self.lassoPoints) > 2:
                    self.finaliseLassoSelection(modifiers)

            return
        if self.currentTool == "transform":
            if self.currentHandle is not None:
                print("[RELEASE] Committing transform scale")

                end = self.mapToScene(event.position().toPoint())
                start = self.dragStartPosition
                dx = end.x() - start.x()
                dy = end.y() - start.y()

                x0, y0, x1, y1 = self.transformBoundingBox
                width = x1 - x0
                height = y1 - y0

                sx = sy = 1.0
                origin_x, origin_y = x0, y0
                h = self.currentHandle

                # Multi-directional transform logic
                if h == 0:  # Top-Left
                    sx = (width - dx) / width
                    sy = (height - dy) / height
                    origin_x, origin_y = x1, y1
                elif h == 1:  # Top-Right
                    sx = (width + dx) / width
                    sy = (height - dy) / height
                    origin_x, origin_y = x0, y1
                elif h == 2:  # Bottom-Right
                    sx = (width + dx) / width
                    sy = (height + dy) / height
                elif h == 3:  # Bottom-Left
                    sx = (width - dx) / width
                    sy = (height + dy) / height
                    origin_x, origin_y = x1, y0
                elif h == 4:  # Top-Center
                    sx = 1.0
                    sy = (height - dy) / height
                    origin_x, origin_y = x0, y1
                elif h == 5:  # Right-Center
                    sx = (width + dx) / width
                    sy = 1.0
                elif h == 6:  # Bottom-Center
                    sx = 1.0
                    sy = (height + dy) / height
                elif h == 7:  # Left-Center
                    sx = (width - dx) / width
                    sy = 1.0
                    origin_x, origin_y = x1, y0
                if self.currentHandle == 8:
                    print("[RELEASE] Commit rotation")

                    if self.rotatedPreview:
                        self.currentLayer.pil_image = self.rotatedPreview

                        if self.rotatedMaskPreview:
                            self.selectionMask = self.rotatedMaskPreview

                            if self.selectionItem:
                                self.customScene.removeItem(self.selectionItem)
                                self.selectionItem = None
                            self.drawSelectionOutline()

                    self.currentLayer.updatePixmap()
                    self.showTransformHandles()
                    self.pushUndo("Rotate")
                    if self.selectionItem:
                        self.selectionItem.setTransform(QTransform())
                    for handle in self.transformationHandles:
                        handle.setTransform(QTransform())

                    self.currentHandle = None
                    self.rotationBackup = None
                    self.pointOfRotation = None
                    self.rotationStartAngle = None
                    self.rotatedPreview = None
                    self.rotatedMaskPreview = None
                    return

                sx = max(0.01, sx)
                sy = max(0.01, sy)

                img = self.transformOriginal
                region = img.crop((x0, y0, x1, y1))
                origin = (int(origin_x), int(origin_y))

                if self.transformationMode == "selection" and self.selectionMask:
                    maskCrop = self.selectionMask.crop((x0, y0, x1, y1))
                    region_cut = Image.composite(region, Image.new("RGBA", region.size, (0, 0, 0, 0)), maskCrop)

                    new_size = (int(region.width * sx), int(region.height * sy))
                    scaled_region = region_cut.resize(new_size, Image.LANCZOS)
                    scaled_mask = maskCrop.resize(new_size, resample=Image.Resampling.NEAREST)

                    result = img.copy()
                    result.paste(Image.new("RGBA", region.size, (0, 0, 0, 0)), (x0, y0))
                    result.paste(scaled_region, origin, scaled_mask)

                    self.currentLayer.pil_image = result

                    newMask = Image.new("L", self.selectionMask.size, 0)
                    newMask.paste(scaled_mask, origin)
                    self.selectionMask = newMask

                    if self.selectionItem:
                        self.customScene.removeItem(self.selectionItem)
                        self.selectionItem = None
                    self.drawSelectionOutline()

                else:
                    new_size = (int(region.width * sx), int(region.height * sy))
                    scaled = region.resize(new_size, resample=Image.LANCZOS)

                    result = img.copy()
                    result.paste(Image.new("RGBA", region.size, (0, 0, 0, 0)), (x0, y0))
                    result.paste(scaled, origin, scaled)
                    self.currentLayer.pil_image = result

                self.currentLayer.updatePixmap()
                self.showTransformHandles()
                self.pushUndo("Scale")

                # Reset state
                self.currentHandle = None
                self.transformOriginal = None
                self.transformBoundingBox = None
                self.dragStartPosition = None
                return

            # Restore: translation release logic
            if self.isSelectionMoving:
                print("[RELEASE] Commit selection move")

                self.isSelectionMoving = False
                self.selectionStartPoint = None
                self.selectionMovedBackup = None

                if self.selectionMovedMask:
                    self.selectionMask = self.selectionMovedMask
                    self.selectionMovedMask = None

                    if self.selectionItem:
                        self.customScene.removeItem(self.selectionItem)
                        self.selectionItem = None
                    self.drawSelectionOutline()

                self.currentLayer.updatePixmap()
                self.showTransformHandles()
                self.pushUndo("Move Selection")
                return

            if self.currentHandle is not None:
                print("[RELEASE] Committing transform scale")

                end = self.mapToScene(event.position().toPoint())
                x0, y0, x1, y1 = self.transformBoundingBox
                width, height = x1 - x0, y1 - y0
                sx = sy = 1.0
                origin = (x0, y0)

                if self.currentHandle == 0:  # top-left
                    sx = (x1 - end.x()) / width
                    sy = (y1 - end.y()) / height
                    origin = (x1, y1)
                elif self.currentHandle == 2:  # bottom-right
                    sx = (end.x() - x0) / width
                    sy = (end.y() - y0) / height
                    origin = (x0, y0)

                img = self.transformOriginal
                region = img.crop((x0, y0, x1, y1))

                if self.transformationMode == "selection" and self.selectionMask:
                    maskCrop = self.selectionMask.crop((x0, y0, x1, y1))
                    region_cut = Image.composite(region, Image.new("RGBA", region.size, (0, 0, 0, 0)), maskCrop)

                    new_size = (max(1, int(region.width * sx)), max(1, int(region.height * sy)))
                    scaled_region = region_cut.resize(new_size, Image.LANCZOS)
                    scaled_mask = maskCrop.resize(new_size, resample=Image.Resampling.NEAREST)

                    result = img.copy()
                    result.paste(Image.new("RGBA", region.size, (0, 0, 0, 0)), (x0, y0))
                    result.paste(scaled_region, (int(origin[0]), int(origin[1])), scaled_mask)

                    self.currentLayer.pil_image = result

                    # Update selection mask
                    newMask = Image.new("L", self.selectionMask.size, 0)
                    newMask.paste(scaled_mask, (int(origin[0]), int(origin[1])))
                    self.selectionMask = newMask

                    # Update marching ants
                    if self.selectionItem:
                        self.customScene.removeItem(self.selectionItem)
                        self.selectionItem = None
                    self.drawSelectionOutline()

                else:  # transform full layer
                    new_size = (max(1, int(region.width * sx)), max(1, int(region.height * sy)))
                    scaled = region.resize(new_size, resample=Image.LANCZOS)

                    result = img.copy()
                    result.paste(Image.new("RGBA", region.size, (0, 0, 0, 0)), (x0, y0))
                    result.paste(scaled, (int(origin[0]), int(origin[1])), scaled)

                    self.currentLayer.pil_image = result

                self.currentLayer.updatePixmap()
                self.showTransformHandles()
                self.pushUndo("Scale")

                # Reset state
                self.currentHandle = None
                self.transformOriginal = None
                self.transformBoundingBox = None
                self.dragStartPosition = None
                return

            if self.isSelectionMoving:
                print("[RELEASE] Commit selection move")

                self.isSelectionMoving = False
                self.selectionStartPoint = None
                self.selectionMovedBackup = None

                if self.selectionMovedMask:
                    self.selectionMask = self.selectionMovedMask
                    self.selectionMovedMask = None

                    # Update marching ants
                    if self.selectionItem:
                        self.customScene.removeItem(self.selectionItem)
                        self.selectionItem = None
                    self.drawSelectionOutline()

                self.currentLayer.updatePixmap()
                self.showTransformHandles()
                self.pushUndo("Move Selection")
                return

        super().mouseReleaseEvent(event)

    def stampBrush(self, x, y):
        """
        Brush/eraser/pencil stamping logic, with support for selection and clipping masks.
        """
        if not self.currentLayer:
            return

        if self.currentTool == "eraser" and self.eraserImage:
            bx, by = self.eraserImage.size
            px = x - bx // 2
            py = y - by // 2

            base = self.currentLayer.pil_image.crop((px, py, px + bx, py + by)).copy()
            eraserAlpha = self.eraserImage.getchannel("A")

            # Clipping + selection mask
            combinedMask = eraserAlpha

            if self.selectionMask:
                selectionCrop = self.selectionMask.crop((px, py, px + bx, py + by))
                combinedMask = ImageChops.multiply(combinedMask, selectionCrop)

            if self.currentLayer.clippingMaskEnabled:
                eraserIndex = self.layers.index(self.currentLayer)
                if eraserIndex > 0:
                    below = self.layers[eraserIndex - 1]
                    belowCrop = below.pil_image.crop((px, py, px + bx, py + by))
                    belowAlpha = belowCrop.getchannel("A")
                    combinedMask = ImageChops.multiply(combinedMask, belowAlpha)
                else:
                    return  # No layer below to clip to

            # Subtract from alpha channel
            r, g, b, a = base.split()
            a = ImageChops.subtract(a, combinedMask)
            base = Image.merge("RGBA", (r, g, b, a))

            self.currentLayer.pil_image.paste(base, (px, py))

        elif self.currentTool == "paintbrush" and self.brushImage:
            bx, by = self.brushImage.size
            px = x - bx // 2
            py = y - by // 2

            region = self.currentLayer.pil_image.crop((px, py, px + bx, py + by))
            blended = Image.alpha_composite(region, self.brushImage)

            # Build combined mask (selection + clipping)
            brushAlpha = self.brushImage.split()[-1]
            combinedMask = brushAlpha

            if self.selectionMask:
                selectionCrop = self.selectionMask.crop((px, py, px + bx, py + by))
                combinedMask = ImageChops.multiply(combinedMask, selectionCrop)

            if self.currentLayer.clippingMaskEnabled:
                brushIndex = self.layers.index(self.currentLayer)
                if brushIndex > 0:
                    below = self.layers[brushIndex - 1]
                    belowCrop = below.pil_image.crop((px, py, px + bx, py + by))
                    belowAlpha = belowCrop.getchannel("A")
                    combinedMask = ImageChops.multiply(combinedMask, belowAlpha)
                else:
                    return  # Nothing to clip to

            self.currentLayer.pil_image.paste(blended, (px, py), combinedMask)

        elif self.currentTool == "pencil" and self.pencilImage:
            bx, by = self.pencilImage.size
            px = x - bx // 2
            py = y - by // 2

            if bx == 1 and by == 1 and self.pencilMode == "draw":
                if 0 <= px < self.currentLayer.pil_image.width and 0 <= py < self.currentLayer.pil_image.height:
                    allowDraw = True

                    if self.selectionMask and self.selectionMask.getpixel((px, py)) == 0:
                        allowDraw = False

                    if self.currentLayer.clippingMaskEnabled:
                        pencilIndex = self.layers.index(self.currentLayer)
                        if pencilIndex > 0:
                            below = self.layers[pencilIndex - 1]
                            belowAlpha = below.pil_image.getchannel("A")
                            if belowAlpha.getpixel((px, py)) == 0:
                                allowDraw = False
                        else:
                            return  # No layer to clip to

                    if allowDraw:
                        self.currentLayer.pil_image.putpixel((px, py), self.penColour)
                return

            # Pencil draw/erase with brush
            if self.pencilMode == "erase":
                base = self.currentLayer.pil_image.crop((px, py, px + bx, py + by)).copy()
                eraserAlpha = self.pencilImage.getchannel("A")
                combinedMask = eraserAlpha

                if self.selectionMask:
                    selectionCrop = self.selectionMask.crop((px, py, px + bx, py + by))
                    combinedMask = ImageChops.multiply(combinedMask, selectionCrop)

                if self.currentLayer.clippingMaskEnabled:
                    idx = self.layers.index(self.currentLayer)
                    if idx > 0:
                        below = self.layers[idx - 1]
                        belowCrop = below.pil_image.crop((px, py, px + bx, py + by))
                        belowAlpha = belowCrop.getchannel("A")
                        combinedMask = ImageChops.multiply(combinedMask, belowAlpha)
                    else:
                        return

                r, g, b, a = base.split()
                a = ImageChops.subtract(a, combinedMask)
                base = Image.merge("RGBA", (r, g, b, a))
                self.currentLayer.pil_image.paste(base, (px, py))

            else:
                region = self.currentLayer.pil_image.crop((px, py, px + bx, py + by))
                blended = Image.alpha_composite(region, self.pencilImage)

                pencilAlpha = self.pencilImage.split()[-1]
                combinedMask = pencilAlpha

                if self.selectionMask:
                    selectionCrop = self.selectionMask.crop((px, py, px + bx, py + by))
                    combinedMask = ImageChops.multiply(combinedMask, selectionCrop)

                if self.currentLayer.clippingMaskEnabled:
                    idx = self.layers.index(self.currentLayer)
                    if idx > 0:
                        below = self.layers[idx - 1]
                        belowCrop = below.pil_image.crop((px, py, px + bx, py + by))
                        belowAlpha = belowCrop.getchannel("A")
                        combinedMask = ImageChops.multiply(combinedMask, belowAlpha)
                    else:
                        return

                self.currentLayer.pil_image.paste(blended, (px, py), combinedMask)




    def floodFill(self, x, y, fillColour, tolerance=0):
        """
        Fills all neighboring pixels within a given colour tolerance and selection mask.
        """
        img = self.currentLayer.pil_image
        pixels = img.load()
        width, height = img.size

        if not (0 <= x < width and 0 <= y < height):
            return

        # Check selection mask first
        if self.selectionMask:
            if self.selectionMask.getpixel((x, y)) == 0:
                return  # Start point is not selected
        if self.currentLayer.clippingMaskEnabled:
            idx = self.layers.index(self.currentLayer)
            if idx > 0:
                below = self.layers[idx - 1]
                belowAlpha = below.pil_image.getchannel("A")
                if belowAlpha.getpixel((x, y)) == 0:
                    return
            else:
                return 
        targetColour = pixels[x, y]
        if targetColour == fillColour:
            return

        def withinBounds(newX, newY):
            return 0 <= newX < width and 0 <= newY < height

        def colourMatch(c1, c2):
            return all(abs(a - b) <= tolerance for a, b in zip(c1, c2))

        queue = [(x, y)]
        visited = set()
        visited.add((x, y))

        while queue:
            cx, cy = queue.pop(0)

            if not withinBounds(cx, cy):
                continue
            if self.currentLayer.clippingMaskEnabled:
                if belowAlpha.getpixel((cx, cy)) == 0:
                    continue
            # Check selection mask at current point
            if self.selectionMask and self.selectionMask.getpixel((cx, cy)) == 0:
                continue

            if not colourMatch(pixels[cx, cy], targetColour):
                continue

            pixels[cx, cy] = fillColour

            for deltaX, deltaY in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                newX, newY = cx + deltaX, cy + deltaY
                if self.currentLayer.clippingMaskEnabled and belowAlpha.getpixel((newX, newY)) == 0:
                    continue
                if withinBounds(newX, newY) and (newX, newY) not in visited:
                    # Check selection mask at neighbor
                    if self.selectionMask and self.selectionMask.getpixel((newX, newY)) == 0:
                        continue
                    queue.append((newX, newY))
                    visited.add((newX, newY))

    def setTool(self, toolName, colour=None):
        """
        Sets the tool as selected in the UI
        """
        self.currentTool = toolName
        if toolName == "paintbrush" and colour:
            self.penColour = colour
            self.updateBrush()
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        if toolName == "fill" and colour:
            self.penColour = colour
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        if toolName == "transform":
            self.showTransformHandles()
        else:
            self.clearTransformHandles()

    def setZoom(self, zoomPercentage):
        """
        Sets the zoom level for the canvas view
        """
        zoomPercentage = max(10, min(zoomPercentage, 4000))
        self.currentZoom = zoomPercentage
        self.zoomFactor = zoomPercentage / 100.0

        visibleRect = self.mapToScene(self.viewport().rect()).boundingRect()
        visibleCentre = visibleRect.center()

        self.resetTransform()
        self.scale(self.zoomFactor, self.zoomFactor)

        self.centerOn(visibleCentre)

        if zoomPercentage > 15:
            self.currentScrollPos = visibleCentre 

        if isinstance(self.customScene, CustomScene):
            self.customScene.update_zoom(zoomPercentage)

        self.viewport().update()

    def autoZoom(self):
        # Get the actual size of the visible area in the view
        viewSize = self.viewport().size()
        viewWidth = viewSize.width()
        viewHeight = viewSize.height()

        # Get canvas size in scene coordinates
        canvasWidth = self.sceneWidth
        canvasHeight = self.sceneHeight

        # Calculate how much we can zoom so the whole canvas fits
        zoom = min(viewWidth / canvasWidth, viewHeight / canvasHeight) * 100

        # Round and apply
        zoomPercent = int(zoom)
        self.setZoom(zoomPercent)

        # Center the view on the canvas
        self.cameraCentre = QPointF(canvasWidth / 2, canvasHeight / 2)
        self.centerOn(self.cameraCentre)

    def toggleGrid(self, enabled):
        """
        Toggles the grid on and off
        """
        self.customScene.gridEnabled = enabled
        self.viewport().update()

    def toggleRuler(self, enabled):
        """
        Toggles the ruler on and off
        """
        self.customScene.rulerEnabled = enabled
        self.viewport().update()

    def snapshotLayers(self):
        """
        Captures and returns a list of the current layers
        """
        return [(layer.name, layer.pil_image.copy()) for layer in self.layers]

    def restoreLayers(self, layer_data):
        """
        Clears the current scrrena and reloads the layers
        """
        self.layers.clear()
        self.customScene.clear()
        for name, image in layer_data:
            layer = Layer(name, image.copy())
            self.addLayer(layer)
        self.currentLayer = self.layers[0] if self.layers else None
        self.viewport().update()

    def pushUndo(self, description):
        """
        Saves the current state of the canvas in the undo stack.
        Clears the redo stack
        """
        print(f"Undo Saved: {description}")
        self.undoStack.append((description, self.snapshotLayers()))
        self.redoStack.clear()

    def undo(self):
        """
        Reverts the canvas to the previous saved state from the undo stack.
        """
        if not self.undoStack:
            print("Nothing to undo.")
            return
        description, previousState = self.undoStack.pop()
        self.redoStack.append((description, self.snapshotLayers()))
        print(f"Undo: {description}")
        self.restoreLayers(previousState)

    def redo(self):
        """
        Redoes the top most item in the stack
        """
        if not self.redoStack:
            print("Nothing to redo.")
            return
        description, nextState = self.redoStack.pop()
        self.undoStack.append((description, self.snapshotLayers()))
        print(f"Redo: {description}")
        self.restoreLayers(nextState)

    def getShapeType(self):
        """
        Retrieves the currently selected Shape type
        """
        try:
            mw = self.window()
            return mw.shapeOptions.shapeDropdown.currentText()
        except:
            return "Line"

    def getShapeWidth(self):
        "Retrives the current line width of the shape"
        try:
            mw = self.window()
            return mw.shapeOptions.lineWidthSlider.value()
        except:
            return 5
        
    def normaliseRect(self, pt1, pt2):
        """
        Enables rectangles and circles to use any coordinates,
        Rather than just enforcing it to drag from top left to bottom right
        """
        x0, y0 = pt1
        x1, y1 = pt2
        left = min(x0, x1)
        top = min(y0, y1)
        right = max(x0, x1)
        bottom = max(y0, y1)
        return (left, top, right, bottom)
    def _update_selection_visual(self, finalise=False):
        if self.selectionItem:
            self.customScene.removeItem(self.selectionItem)

        if self.selectionRectangle:
            print("Drawing selection:", self.selectionRectangle)
            pen = QPen(QColor(0, 120, 215), 1)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([4, 4])
            pen.setDashOffset(self.selectionLineDashes)
            self.selectionItem = QGraphicsRectItem(self.selectionRectangle)
            self.selectionItem.setZValue(1000)
            self.selectionItem.setPen(pen)
            self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.customScene.addItem(self.selectionItem)

        if finalise:
            print("Final selection rect:", self.selectionRectangle)

    def animateSelection(self):
        if self.selectionItem:
            self.selectionLineDashes = (self.selectionLineDashes + 1) % 20
            pen = self.selectionItem.pen()
            pen.setDashOffset(self.selectionLineDashes)
            self.selectionItem.setPen(pen)
            self.viewport().update()
        if not self.selectionItem or not self.selectionRectangle:
            return
    def generateSelectionMask(self):
        if not self.selectionRectangle:
            return

        width, height = self.sceneWidth, self.sceneHeight
        newMask = Image.new("L", (width, height), 0)
        rect = self.selectionRectangle.toRect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        ImageDraw.Draw(newMask).rectangle([x, y, x + w, y + h], fill=255)

        self.selectionMask = self.combineSelectionMasks(newMask)

    def applySelectionAsMask(self):
        canvas = self.currentCanvas()
        if not canvas or not canvas.selectionMask or not canvas.currentLayer:
            return

        layer = canvas.currentLayer
        img = layer.pil_image.convert("RGBA")

        r, g, b, a = img.split()
        newAlpha = ImageChops.multiply(a, canvas.selectionMask)
        layer.pil_image = Image.merge("RGBA", (r, g, b, newAlpha))

        layer.updatePixmap()
        canvas.viewport().update()
    def finaliseMarqueeSelection(self, modifiers=Qt.KeyboardModifier.NoModifier):
        if not self.selectionRectangle:
            return

        width, height = self.sceneWidth, self.sceneHeight
        newMask = Image.new("L", (width, height), 0)
        rect = self.selectionRectangle.toRect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        ImageDraw.Draw(newMask).rectangle([x, y, x + w, y + h], fill=255)

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if self.selectionMask:
                self.selectionMask = ImageChops.lighter(self.selectionMask, newMask)
            else:
                self.selectionMask = newMask
            print("Added to selection.")
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            if self.selectionMask:
                inverted = ImageChops.invert(newMask)
                self.selectionMask = ImageChops.multiply(self.selectionMask, inverted)
            else:
                self.selectionMask = Image.new("L", (width, height), 0)
            print("Subtracted from selection.")
        else:
            self.selectionMask = newMask
            print("Replaced selection.")

        if self.selectionItem:
            self.customScene.removeItem(self.selectionItem)
            self.selectionItem = None

        # Regenerate the selection outline from the final mask
        mask_np = np.array(self.selectionMask)
        contours = cv2.findContours(mask_np, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)[0]

        path = QPainterPath()
        for contour in contours:
            if len(contour) >= 2:
                contour = contour.squeeze()
                if len(contour.shape) == 1:
                    path.moveTo(contour[0], contour[1])
                else:
                    path.moveTo(contour[0][0], contour[0][1])
                    for pt in contour[1:]:
                        path.lineTo(pt[0], pt[1])

        self.selectionItem = QGraphicsPathItem(path)
        pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self.selectionLineDashes)
        self.selectionItem.setPen(pen)
        self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.selectionItem.setZValue(1000)
        self.customScene.addItem(self.selectionItem)
        print("Marquee selection finalized.")


    def finaliseLassoSelection(self, modifiers=Qt.KeyboardModifier.NoModifier):
        width, height = self.sceneWidth, self.sceneHeight
        newMask = Image.new("L", (width, height), 0)

        polygon = [(pt.x(), pt.y()) for pt in self.lassoPoints]
        if len(polygon) < 3:
            return  # Not enough points for valid polygon
        if polygon[0] != polygon[-1]:
            polygon.append(polygon[0])  # close the shape

        ImageDraw.Draw(newMask).polygon(polygon, fill=255)

        # Combine with existing selection mask
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if self.selectionMask:
                self.selectionMask = ImageChops.lighter(self.selectionMask, newMask)
            else:
                self.selectionMask = newMask
            print("Added to selection.")
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            if self.selectionMask:
                inverted = ImageChops.invert(newMask)
                self.selectionMask = ImageChops.multiply(self.selectionMask, inverted)
            else:
                self.selectionMask = Image.new("L", (width, height), 0)
            print("Subtracted from selection.")
        else:
            self.selectionMask = newMask
            print("Replaced selection.")

        # Remove old selection visuals
        if self.selectionItem:
            self.customScene.removeItem(self.selectionItem)
            self.selectionItem = None
        if self.lassoPathItem:
            self.customScene.removeItem(self.lassoPathItem)
            self.lassoPathItem = None

        # Create visual outline of entire combined selection
        mask_np = np.array(self.selectionMask)
        contours = cv2.findContours(mask_np, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)[0]

        path = QPainterPath()
        for contour in contours:
            if len(contour) >= 2:
                contour = contour.squeeze()
                if len(contour.shape) == 1:
                    path.moveTo(contour[0], contour[1])
                else:
                    path.moveTo(contour[0][0], contour[0][1])
                    for pt in contour[1:]:
                        path.lineTo(pt[0], pt[1])

        self.selectionItem = QGraphicsPathItem(path)
        pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self.selectionLineDashes)
        self.selectionItem.setPen(pen)
        self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.selectionItem.setZValue(1000)
        self.customScene.addItem(self.selectionItem)
        print("Lasso selection finalized.")

    def clearSelection(self):
        self.selectionMask = None
        self.selectionRectangle = None
        self.lassoPoints = []

        if self.selectionItem:
            self.customScene.removeItem(self.selectionItem)
            self.selectionItem = None

        if self.lassoPathItem:
            self.customScene.removeItem(self.lassoPathItem)
            self.lassoPathItem = None

        print("Selection cleared.")

    def combineSelectionMasks(self, newMask):

        if self.selectionMode == "add" and self.selectionMask:
            return ImageChops.lighter(self.selectionMask, newMask)
        elif self.selectionMode == "subtract" and self.selectionMask:
            return ImageChops.subtract(self.selectionMask, newMask)
        else:  # "replace" or no existing mask
            return newMask
        
    def selectAllColour(self, targetColour):
        width, height = self.sceneWidth, self.sceneHeight
        img = self.currentLayer.pil_image.convert("RGBA")
        pixels = np.array(img)

        match = np.all(pixels[:, :, :3] == targetColour[:3], axis=-1)
        newMask_np = np.where(match, 255, 0).astype(np.uint8)
        newMask = Image.fromarray(newMask_np, mode="L")

        self.selectionMask = ImageChops.lighter(self.selectionMask, newMask) if self.selectionMask else newMask

        # Regenerate selection outline
        if self.selectionItem:
            self.customScene.removeItem(self.selectionItem)
            self.selectionItem = None

        contours, _ = cv2.findContours(newMask_np, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        path = QPainterPath()
        for contour in contours:
            if len(contour) >= 2:
                contour = contour.squeeze()
                if len(contour.shape) == 1:
                    continue
                path.moveTo(contour[0][0], contour[0][1])
                for pt in contour[1:]:
                    path.lineTo(pt[0], pt[1])
                path.closeSubpath()

        self.selectionItem = QGraphicsPathItem(path)
        pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self.selectionLineDashes)
        self.selectionItem.setPen(pen)
        self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.selectionItem.setZValue(1000)
        self.customScene.addItem(self.selectionItem)

        print(f"Selected all pixels of colour {targetColour}")

    def showTransformHandles(self):
        if not self.currentLayer:
            return

        # Remove old handles
        for handle in getattr(self, 'transformationHandles', []):
            self.customScene.removeItem(handle)
        self.transformationHandles = []

        # Get bounding box: selection or full layer
        if self.selectionMask:
            bbox = self.selectionMask.getbbox()
            if not bbox:
                return
            x0, y0, x1, y1 = bbox
            self.transformationMode = "selection"
        else:
            x0, y0 = 0, 0
            x1, y1 = self.currentLayer.pil_image.width, self.currentLayer.pil_image.height
            self.transformationMode = "layer"

        self.transformBoundingBox = (x0, y0, x1, y1)

        # Handle positions (your layout)
        points = [
            (x0, y0),                     # 0 top-left
            (x1, y0),                     # 1 top-right
            (x1, y1),                     # 2 bottom-right
            (x0, y1),                     # 3 bottom-left
            ((x0 + x1) / 2, y0),          # 4 top-center
            (x1, (y0 + y1) / 2),          # 5 right-center
            ((x0 + x1) / 2, y1),          # 6 bottom-center
            (x0, (y0 + y1) / 2),          # 7 left-center
        ]

        for i, (px, py) in enumerate(points):
            handle = QGraphicsRectItem(-5, -5, 10, 10)
            handle.setBrush(QBrush(QColor(255, 255, 255)))
            handle.setPen(QPen(Qt.GlobalColor.black, 1))
            handle.setZValue(2000)
            handle.setPos(px, py)
            self.customScene.addItem(handle)
            self.transformationHandles.append(handle)

        # Add rotation handle (index 8)
        rx = (x0 + x1) / 2
        ry = y0 - 30  # 30 pixels above top
        rotateHandle = QGraphicsRectItem(-6, -6, 12, 12)
        rotateHandle.setBrush(QBrush(QColor(200, 50, 50)))  # red handle
        rotateHandle.setPen(QPen(Qt.GlobalColor.black, 1))
        rotateHandle.setZValue(2000)
        rotateHandle.setPos(rx, ry)
        self.customScene.addItem(rotateHandle)
        self.transformationHandles.append(rotateHandle)

    def clearTransformHandles(self):
        for handle in self.transformationHandles:
            self.customScene.removeItem(handle)
        self.transformationHandles.clear()
    def drawSelectionOutline(self):
        if not self.selectionMask:
            return

        mask_np = np.array(self.selectionMask)
        contours, _ = cv2.findContours(mask_np, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        path = QPainterPath()
        for contour in contours:
            contour = contour.squeeze()
            if contour.ndim != 2:
                continue
            path.moveTo(contour[0][0], contour[0][1])
            for pt in contour[1:]:
                path.lineTo(pt[0], pt[1])
            path.closeSubpath()

        self.selectionItem = QGraphicsPathItem(path)
        pen = QPen(QColor(0, 120, 215), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        pen.setDashPattern([4, 4])
        pen.setDashOffset(self.selectionLineDashes)
        self.selectionItem.setPen(pen)
        self.selectionItem.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.selectionItem.setZValue(1000)
        self.customScene.addItem(self.selectionItem)



# --- CanvasTabWidget: Contains a Canvas and its own zoom controls ---
class CanvasTabWidget(QWidget):
    def __init__(self, canvasWidth, canvasHeight, gridEnabled, rulerEnabled, bgImg=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # Create the canvas.
        self.canvas = Canvas(sceneWidth=canvasWidth, sceneHeight=canvasHeight, gridEnabled=gridEnabled, rulerEnabled=rulerEnabled)
        # Add a background layer.
        if bgImg:
            bgImg = bgImg.resize((canvasWidth, canvasHeight))
        else:
            bgImg = Image.new("RGBA", (canvasWidth, canvasHeight), (255, 255, 255, 255))
        layer = Layer("Layer 1", bgImg)
        self.canvas.addLayer(layer)
        self.canvas.currentLayer = self.canvas.layers[0]
        layout.addWidget(self.canvas)

        # Create a zoom control bar unique to this canvas.
        zoomLayout = QHBoxLayout()
        self.zoomOutBtn = QPushButton("-")
        self.zoomInBtn = QPushButton("+")
        self.zoomEdit = QLineEdit("100")
        self.zoomEdit.setFixedWidth(50)
        self.zoomOutBtn.clicked.connect(self.zoomOut)
        self.zoomInBtn.clicked.connect(self.zoomIn)
        self.zoomEdit.returnPressed.connect(self.zoomTextChanged)
        zoomLayout.addWidget(self.zoomOutBtn)
        zoomLayout.addWidget(self.zoomInBtn)
        zoomLayout.addWidget(self.zoomEdit)
        layout.addLayout(zoomLayout)

    def zoomIn(self):
        try:
            zoom = int(self.zoomEdit.text())
        except ValueError:
            zoom = 100
        zoom += 10
        self.zoomEdit.setText(str(zoom))
        self.canvas.setZoom(zoom)

    def zoomOut(self):
        try:
            zoom = int(self.zoomEdit.text())
        except ValueError:
            zoom = 100
        zoom = max(10, zoom - 10)
        self.zoomEdit.setText(str(zoom))
        self.canvas.setZoom(zoom)

    def zoomTextChanged(self):
        try:
            zoom = abs(int(self.zoomEdit.text()))
        except ValueError:
            zoom = 100
            self.zoomEdit.setText(str(zoom))
        self.canvas.setZoom(zoom)

# --- Tool Option Panels ---
class PaintbrushOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Paintbrush Options:"))
        self.brushSelector = QComboBox()
        layout.addWidget(QLabel("Brush:"))
        layout.addWidget(self.brushSelector)
        layout.addWidget(QLabel("Size:"))
        self.brushSizeSlider = QSlider(Qt.Orientation.Horizontal)
        self.brushSizeSlider.setMinimum(1)
        self.brushSizeSlider.setMaximum(500)
        self.brushSizeSlider.setValue(50)
        layout.addWidget(self.brushSizeSlider)
        self.brushOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.brushOpacitySlider.setMinimum(0)
        self.brushOpacitySlider.setMaximum(255)
        self.brushOpacitySlider.setValue(255)
        layout.addWidget(QLabel("Opacity:"))
        layout.addWidget(self.brushOpacitySlider)
        layout.addWidget(QLabel("Spacing:"))
        self.brushSpacingSlider = QSlider(Qt.Orientation.Horizontal)
        self.brushSpacingSlider.setMinimum(1)
        self.brushSpacingSlider.setMaximum(50)
        self.brushSpacingSlider.setValue(1)
        layout.addWidget(self.brushSpacingSlider)
        

class EraserOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Eraser Options:"))
        self.eraserSelector = QComboBox()
        layout.addWidget(QLabel("Eraser:"))
        layout.addWidget(self.eraserSelector)
        layout.addWidget(QLabel("Size:"))
        self.eraserSizeSlider = QSlider(Qt.Orientation.Horizontal)
        self.eraserSizeSlider.setMinimum(1)
        self.eraserSizeSlider.setMaximum(500)
        self.eraserSizeSlider.setValue(5)
        layout.addWidget(self.eraserSizeSlider)
        self.eraserOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.eraserOpacitySlider.setMinimum(0)
        self.eraserOpacitySlider.setMaximum(255)
        self.eraserOpacitySlider.setValue(255)
        layout.addWidget(QLabel("Opacity:"))
        layout.addWidget(self.eraserOpacitySlider)
        layout.addWidget(QLabel("Spacing:"))
        self.eraserOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.eraserOpacitySlider.setMinimum(1)
        self.eraserOpacitySlider.setMaximum(50)
        self.eraserOpacitySlider.setValue(1)
        layout.addWidget(self.eraserOpacitySlider)

class PencilOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Pencil Options:"))
        self.pencilSelector = QComboBox()
        layout.addWidget(QLabel("Pencil:"))
        layout.addWidget(self.pencilSelector)
        layout.addWidget(QLabel("Size:"))
        self.pencilSizeSlider = QSlider(Qt.Orientation.Horizontal)
        self.pencilSizeSlider.setMinimum(1)
        self.pencilSizeSlider.setMaximum(500)
        self.pencilSizeSlider.setValue(50)
        layout.addWidget(self.pencilSizeSlider)
        self.PencilOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.PencilOpacitySlider.setMinimum(0)
        self.PencilOpacitySlider.setMaximum(255)
        self.PencilOpacitySlider.setValue(255)
        layout.addWidget(QLabel("Opacity:"))
        layout.addWidget(self.PencilOpacitySlider)
        layout.addWidget(QLabel("Spacing:"))
        self.PencilSpacingSlider = QSlider(Qt.Orientation.Horizontal)
        self.PencilSpacingSlider.setMinimum(1)
        self.PencilSpacingSlider.setMaximum(50)
        self.PencilSpacingSlider.setValue(1)
        layout.addWidget(self.PencilSpacingSlider)
        self.toggle_btn = QPushButton("Switch to Erase")
        layout.addWidget(self.toggle_btn)

class MoveOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Move view"))

class FillOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Fill Tool"))

class ShapeOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.shapeDropdown = QComboBox()
        self.shapeDropdown.addItems(["Line", "Rectangle", "Circle"])
        layout.addWidget(self.shapeDropdown)

        layout.addWidget(QLabel("Line Size:"))
        self.lineWidthSlider = QSlider(Qt.Orientation.Horizontal)
        self.lineWidthSlider.setMinimum(1)
        self.lineWidthSlider.setMaximum(50)
        self.lineWidthSlider.setValue(5)
        layout.addWidget(self.lineWidthSlider)

class TransformOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Transform Tools"))
        self.flipHorizontalButton = QPushButton("Flip H")
        layout.addWidget(self.flipHorizontalButton)
        self.flipVerticalButton = QPushButton("Flip V")
        layout.addWidget(self.flipVerticalButton)
        self.shearButton = QPushButton("Shear")
        layout.addWidget(self.shearButton)

class SelectionOptions(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Selection Tools"))
        self.marqueeButton = QPushButton("Marquee")
        self.marqueeButton.setCheckable(True)
        self.lassoButton = QPushButton("Lasso")
        self.lassoButton.setCheckable(True)
        layout.addWidget(self.marqueeButton)
        layout.addWidget(self.lassoButton)
        self.deselectButton = QPushButton("deselect")
        layout.addWidget(self.deselectButton)
        self.selectButton = QPushButton("Select by Colour")
        layout.addWidget(self.selectButton)
        self.selectedColour = QColor(0, 0, 0, 255)


def generateLayerName(existingNames, prefix="Layer"):
    index = 1
    while f"{prefix} {index}" in existingNames:
        index += 1
    return f"{prefix} {index}"

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self, canvasWidth=2000, canvasHeight=2000, bgImg=None):
        super().__init__()
        self.setWindowTitle("Iteration 3")
        self.resize(1200, 800)

        # Central tab widget holds multiple canvas tabs.
        self.tabWidget = QTabWidget(self)
        self.setCentralWidget(self.tabWidget)
        self.tabWidget.currentChanged.connect(self.updateLayerList)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)

        # Menus.
        self.createMenus()
        self.savedFilePath = None
        self.lastSaveTime = 0
        self.selectionClipboard = None

        # Dock widget for colour picker and layer list.
        self.createRightDock()

        # Top toolbar for tool-specific options.
        self.toolOptionsStack = QStackedWidget(self)
        self.paintbrush_options = PaintbrushOptions(self)
        self.eraser_options = EraserOptions(self)
        self.pencil_options = PencilOptions(self)
        self.move_options = MoveOptions(self)
        self.fill_options = FillOptions(self)
        self.shape_options = ShapeOptions(self)
        self.selection_options = SelectionOptions(self)
        self.transform_options = TransformOptions(self)

        self.toolOptionsStack.addWidget(self.paintbrush_options)
        self.paintbrush_options.brushSizeSlider.valueChanged.connect(self.updateBrushSize)
        self.paintbrush_options.brushOpacitySlider.valueChanged.connect(self.updateBrushOpacity)
        self.populateBrushes(self.paintbrush_options.brushSelector)
        self.paintbrush_options.brushSelector.currentTextChanged.connect(self.onBrushImageChanged)
        self.paintbrush_options.brushSpacingSlider.valueChanged.connect(self.updateBrushSpacing)

        self.toolOptionsStack.addWidget(self.eraser_options)
        self.eraser_options.eraserSizeSlider.valueChanged.connect(self.updateEraserSize)
        self.eraser_options.eraserOpacitySlider.valueChanged.connect(self.updateBrushSpacing)
        self.populateBrushes(self.eraser_options.eraserSelector)
        self.eraser_options.eraserSelector.currentTextChanged.connect(self.onEraserImageChanged)
        self.eraser_options.eraserOpacitySlider.valueChanged.connect(self.updateEraserSpacing)

        self.toolOptionsStack.addWidget(self.pencil_options)
        self.pencil_options.pencilSizeSlider.valueChanged.connect(self.updatePencilSize)
        self.pencil_options.PencilOpacitySlider.valueChanged.connect(self.updatePencilOpacity)
        self.populateBrushes(self.pencil_options.pencilSelector)
        self.pencil_options.pencilSelector.currentTextChanged.connect(self.onPencilImageChanged)
        self.pencil_options.PencilSpacingSlider.valueChanged.connect(self.updatePencilSpacing)
        self.pencil_options.toggle_btn.clicked.connect(self.togglePencilMode)

        self.toolOptionsStack.addWidget(self.move_options)

        self.toolOptionsStack.addWidget(self.fill_options)

        self.toolOptionsStack.addWidget(self.shape_options)

        self.toolOptionsStack.addWidget(self.transform_options)
        self.transform_options.flipHorizontalButton.clicked.connect(self.flipHorizontal)
        self.transform_options.flipVerticalButton.clicked.connect(self.flipVertical)
        self.transform_options.shearButton.clicked.connect(self.showShearDialog)

        self.toolOptionsStack.addWidget(self.selection_options)
        self.selection_options.marqueeButton.clicked.connect(lambda: self.setSelectionTool("marquee"))
        self.selection_options.lassoButton.clicked.connect(lambda: self.setSelectionTool("lasso"))
        self.selection_options.deselectButton.clicked.connect(self.clearSelection)
        self.selection_options.selectButton.clicked.connect(self.selectByColour)

        self.tool_options_tb = QToolBar("Tool Options", self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.tool_options_tb)
        self.tool_options_tb.addWidget(self.toolOptionsStack)
        self.toolOptionsStack.setCurrentIndex(0)

        # Left toolbar for main tools.
        self.toolsToolBar = QToolBar("Tools", self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolsToolBar)
        self.toolGroup = QActionGroup(self)
        self.toolGroup.setExclusive(True)
        
        self.paintbrushAction = QAction("Paintbrush", self, checkable=True)
        self.paintbrushAction.triggered.connect(lambda: self.selectTool("paintbrush"))
        self.toolsToolBar.addAction(self.paintbrushAction)
        self.toolGroup.addAction(self.paintbrushAction)
        
        self.eraserAcrion = QAction("Eraser", self, checkable=True)
        self.eraserAcrion.triggered.connect(lambda: self.selectTool("eraser"))
        self.toolsToolBar.addAction(self.eraserAcrion)
        self.toolGroup.addAction(self.eraserAcrion)

        self.pencilAction = QAction("Pencil", self, checkable=True)
        self.pencilAction.triggered.connect(lambda: self.selectTool("pencil"))
        self.toolsToolBar.addAction(self.pencilAction)
        self.toolGroup.addAction(self.pencilAction)
        
        self.moveAction = QAction("Move", self, checkable=True)
        self.moveAction.triggered.connect(lambda: self.selectTool("move"))
        self.toolsToolBar.addAction(self.moveAction)
        self.toolGroup.addAction(self.moveAction)
        
        self.fillAction = QAction("Fill", self, checkable=True)
        self.fillAction.triggered.connect(lambda: self.selectTool("fill"))
        self.toolsToolBar.addAction(self.fillAction)
        self.toolGroup.addAction(self.fillAction)

        self.shapesAction = QAction("Shapes", self, checkable=True)
        self.shapesAction.triggered.connect(lambda: self.selectTool("shape"))
        self.toolsToolBar.addAction(self.shapesAction)
        self.toolGroup.addAction(self.shapesAction)

        self.selectionAction = QAction("Selection", self, checkable=True)
        self.selectionAction.triggered.connect(lambda: self.selectTool("selection"))
        self.toolsToolBar.addAction(self.selectionAction)
        self.toolGroup.addAction(self.selectionAction)

        self.transformAction = QAction("Transform", self, checkable=True)
        self.transformAction.triggered.connect(lambda: self.selectTool("transform"))
        self.toolsToolBar.addAction(self.transformAction)
        self.toolGroup.addAction(self.transformAction)

        self.paintbrushAction.setChecked(True)
        self.currentTool = "paintbrush"

        self.globalGridEnabled = False
        self.globalRulerEnabled = False

        # Add the initial canvas tab.
        self.addNewCanvas(canvasWidth, canvasHeight, bgImg)

    def createMenus(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("File")
        newTabAction = QAction("New...", self)
        newTabAction.triggered.connect(self.newTab)
        fileMenu.addAction(newTabAction)
        
        openAction = QAction("Open Image as Layer...", self)
        openAction.triggered.connect(self.openFile)
        fileMenu.addAction(openAction)

        quickSaveAction = QAction("Save...", self)
        quickSaveAction.triggered.connect(self.quickSaveFile)
        fileMenu.addAction(quickSaveAction)
        saveAction = QAction("Save Image As...", self)
        saveAction.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAction)
        saveLayersAction = QAction("Save All Layers...", self)
        saveLayersAction.triggered.connect(self.saveAllLayers)
        fileMenu.addAction(saveLayersAction)
        fileMenu.addSeparator()
        
        exitAction = QAction("Exit", self)
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        editMenu = menubar.addMenu("Edit")
        undoAction = QAction("Undo", self)
        redoAction = QAction("Redo", self)
        undoAction.setShortcut("Ctrl+Z")
        undoAction.triggered.connect(self.undoUI)
        redoAction.triggered.connect(self.redoUI)
        editMenu.addAction(undoAction)
        editMenu.addAction(redoAction)
        editMenu.addSeparator()
        copyAction = QAction("Copy", self)
        copyAction.setShortcut("Ctrl+C")
        copyAction.triggered.connect(self.copySelection)
        editMenu.addAction(copyAction)
        cutAction = QAction("Cut", self)
        cutAction.setShortcut("Ctrl+X")
        cutAction.triggered.connect(self.cutSelection)
        editMenu.addAction(cutAction)
        pasteAction = QAction("Paste", self)
        pasteAction.setShortcut("Ctrl+V")
        pasteAction.triggered.connect(self.pasteClipboard)
        editMenu.addAction(pasteAction)

        viewMenu = menubar.addMenu("View")
        self.toggleGridAction = QAction("Show Grid", self, checkable=True)
        self.toggleGridAction.setChecked(False)
        self.toggleGridAction.triggered.connect(self.toggleGrid)
        viewMenu.addAction(self.toggleGridAction)

        self.toggleRulerAction = QAction("Show Ruler", self, checkable=True)
        self.toggleRulerAction.setChecked(False)
        self.toggleRulerAction.triggered.connect(self.toggleRuler)
        viewMenu.addAction(self.toggleRulerAction)

    def createRightDock(self):
        self.rightDock = QDockWidget("Colour and Layers", self)
        self.rightDock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.rightDock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        rightWidget = QWidget()
        rightLayout = QVBoxLayout(rightWidget)
        self.colourButton = QPushButton("Choose Colour")
        self.colourButton.clicked.connect(self.chooseColour)
        rightLayout.addWidget(self.colourButton)
        self.addLayerButton = QPushButton("Add Blank Layer")
        self.addLayerButton.clicked.connect(self.addBlankLayer)
        rightLayout.addWidget(self.addLayerButton)
        self.deleteLayerButton = QPushButton("Delete Selected Layer")
        self.deleteLayerButton.clicked.connect(self.deleteSelectedLayer)
        rightLayout.addWidget(self.deleteLayerButton)
        self.opacityLabel = QLabel("Layer Opacity:")
        self.layerOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.layerOpacitySlider.setMinimum(0)
        self.layerOpacitySlider.setMaximum(255)
        self.layerOpacitySlider.setValue(255)
        self.layerOpacitySlider.valueChanged.connect(self.changeLayerOpacity)
        rightLayout.addWidget(self.opacityLabel)
        rightLayout.addWidget(self.layerOpacitySlider)
        self.clippingMaskBtn = QPushButton("Enable Clipping Mask")
        self.clippingMaskBtn.clicked.connect(self.toggleClippingMask)
        rightLayout.addWidget(self.clippingMaskBtn)

        self.blendModeLabel = QLabel("Blend Mode:")
        self.blendModeDropdown = QComboBox()
        self.blendModeDropdown.addItems(BLEND_MODE_MAP.keys())
        self.blendModeDropdown.currentTextChanged.connect(self.changeLayerBlendMode)

        rightLayout.addWidget(self.blendModeLabel)
        rightLayout.addWidget(self.blendModeDropdown)
        # Global layer list; its content is updated when the tab changes.
        self.layerList = QListWidget()
        self.layerList.setDragDropMode(QListWidget.DragDropMode.InternalMove)  
        self.layerList.model().rowsMoved.connect(self.onLayersReordered)
        self.layerList.currentRowChanged.connect(self.onLayerSelectionChanged)
        self.layerList.itemSelectionChanged.connect(self.SaveLayerSelection)
        rightLayout.addWidget(self.layerList)
        self.rightDock.setWidget(rightWidget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.rightDock)

    def addNewCanvas(self, canvasWidth, canvasHeight, bgImg=None):
        tab = CanvasTabWidget(
            canvasWidth, canvasHeight, gridEnabled=self.globalGridEnabled,rulerEnabled=self.globalRulerEnabled,
            bgImg=bgImg
        )
        self.tabWidget.addTab(tab, f"Canvas {self.tabWidget.count()+1}")
        self.tabWidget.setCurrentWidget(tab)
        self.updateLayerList()

    def newTab(self):
        startup = StartupDialog()
        if startup.exec() == QDialog.DialogCode.Accepted:
            data = startup.getData()
            if data[0] == "custom":
                canvasWidth, canvasHeight = data[1], data[2]
                bgImg = None
            elif data[0] == "image":
                try:
                    bgImg = Image.open(data[1]).convert("RGBA")
                    canvasWidth, canvasHeight = bgImg.size
                except Exception as e:
                    print(f"Error loading image: {e}")
                    canvasWidth, canvasHeight = 2000, 2000
                    bgImg = None
            self.addNewCanvas(canvasWidth, canvasHeight, bgImg)

    def currentCanvas(self):
        widget = self.tabWidget.currentWidget()
        if widget and hasattr(widget, "canvas"):
            return widget.canvas
        return None
    
    def closeTab(self, index):
        # Close the tab at the given index
        widget = self.tabWidget.widget(index)
        if widget:
            widget.deleteLater()  # Remove the widget from the layout
        self.tabWidget.removeTab(index)

    def updateLayerList(self):
        canvas = self.currentCanvas()
        if not canvas:
            return

        self.layerList.blockSignals(True)
        self.layerList.clear()

        for layer in canvas.layers:
            self.layerList.addItem(layer.name)

        self.layerList.setCurrentRow(0)
        canvas.currentLayer = canvas.layers[0] if canvas.layers else None

        self.layerList.blockSignals(False)

    def saveFile(self):
        """
        Save the current image to a specified file path.
        Ensures the file path is valid and doesn't have invalid schemes.
        """
        canvas = self.currentCanvas() 
        if not canvas:
            print("Error: No canvas available.")
            return
        options = QFileDialog.Option.DontUseNativeDialog
        FileName, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;BMP Files (*.bmp)")
        if not FileName:
            print("Error: No file selected.")
            return
        if FileName.startswith("data:"):
            print(f"Error: Invalid file scheme (data URL) - {FileName}")
            return
        if not FileName.lower().endswith(('.png', '.jpg', '.bmp')):
            print("Warning: File extension is not valid. Adding .png as default.")
            FileName += ".png"  # Add a .png extension if not already present
        try:
            width = canvas.sceneWidth
            height = canvas.sceneHeight
            finalImage = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            for layer in canvas.layers:
                finalImage.paste(layer.pil_image, (0, 0), layer.pil_image)
            finalImage.save(FileName)
            canvas.savedFilePath = FileName
            canvas.lastSaveTime = time.time()
            print(f"Image saved as {FileName}")
        except Exception as e:
            print(f"Error saving image: {e}") 

    def quickSaveFile(self):
        canvas = self.currentCanvas()
        if not canvas:
            return
        if not hasattr(canvas, 'savedFilePath') or not canvas.savedFilePath:
            self.saveFile() 
            return
        try:
            width = canvas.sceneWidth
            height = canvas.sceneHeight
            finalImage = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            for layer in canvas.layers:
                finalImage.paste(layer.pil_image, (0, 0), layer.pil_image)

            finalImage.save(canvas.savedFilePath)
            canvas.lastSaveTime = time.time()
            print(f"[Quick Save] Saved to {canvas.savedFilePath}")
        except Exception as e:
            print(f"[Quick Save Error]: {e}")
            
    def saveAllLayers(self):
        canvas = self.currentCanvas()
        if not canvas:
            return
        folderNmae = QFileDialog.getExistingDirectory(self, "Select Folder to Save Layers")
        if not folderNmae:
            return

        for i, layer in enumerate(canvas.layers):
            path = os.path.join(folderNmae, f"{layer.name.replace(' ', '_')}_{i+1}.png")
            try:
                layer.pil_image.save(path)
            except Exception as e:
                print(f"Error saving layer {layer.name}: {e}")
        print(f"All layers saved to {folderNmae}")

    def closeTab(self, index):
        widget = self.tabWidget.widget(index)
        if widget and hasattr(widget, "canvas"):
            elapsed = time.time() - getattr(widget.canvas, 'lastSaveTime', 0)
            if elapsed > 10:  # arbitrary "unsaved" threshold (10 seconds)
                reply = QMessageBox.question(self, "Unsaved Changes", "This tab may have unsaved changes.\nClose anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
            widget.deleteLater()
        self.tabWidget.removeTab(index)
    
    def openFile(self):
        canvas = self.currentCanvas()
        if not canvas:
            print("Error: No canvas available.")
            return
        options = QFileDialog.Option.DontUseNativeDialog
        FileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if not FileName:
            return

        try:
            image = Image.open(FileName).convert("RGBA")
            canvas.pushUndo("Add Image Layer")
            layerName = f"Layer {len(canvas.layers) + 1}"
            layer = Layer(layerName, image)
            canvas.addLayer(layer)
            self.updateLayerList()
            canvas.currentLayer = canvas.layers[-1]
            print("Loading image from:", FileName)
        except Exception as e:
            print(f"Error opening image: {e}")

    def selectTool(self, toolName):
        self.currentTool = toolName
        canvas = self.currentCanvas()
        if canvas:
            canvas.setTool(toolName, colour=canvas.penColour)
        if toolName == "paintbrush":
            self.toolOptionsStack.setCurrentWidget(self.paintbrush_options)
        elif toolName == "eraser":
            self.toolOptionsStack.setCurrentWidget(self.eraser_options)
        if toolName == "pencil":
            self.toolOptionsStack.setCurrentWidget(self.pencil_options)
        elif toolName == "move":
            self.toolOptionsStack.setCurrentWidget(self.move_options)
        elif toolName == "fill":
            self.toolOptionsStack.setCurrentWidget(self.fill_options)
        elif toolName == "shape":
            self.toolOptionsStack.setCurrentWidget(self.shape_options)
        elif toolName == "selection":
            self.toolOptionsStack.setCurrentWidget(self.selection_options)
        elif toolName == "transform":
            self.toolOptionsStack.setCurrentWidget(self.transform_options)
        print(f"Switched to {toolName} tool.")

    def chooseColour(self):
        colour = QColorDialog.getColor()
        if colour.isValid():
            rgba = (colour.red(), colour.green(), colour.blue(), colour.alpha())
            canvas = self.currentCanvas()
            if canvas:
                canvas.penColour = rgba
                if self.currentTool == "paintbrush":
                    canvas.setTool("paintbrush", colour=rgba)


    def addBlankLayer(self):
        canvas = self.currentCanvas()
        if not canvas:
            return
        canvas.pushUndo("Add Blank Layer")
        cw, ch = canvas.sceneWidth, canvas.sceneHeight
        image = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        existingNames = [layer.name for layer in canvas.layers]
        layerName = generateLayerName(existingNames, prefix="Layer")
        layer = Layer(layerName, image, layerOpacity=255, blendMode="Normal")
        canvas.addLayer(layer)
        self.updateLayerList()

    def deleteSelectedLayer(self):
        canvas = self.currentCanvas()
        if not canvas:
            return

        selectedItems = self.layerList.selectedItems()
        if not selectedItems:
            return

        indexes2Remove = [self.layerList.row(item) for item in selectedItems]
        indexes2Remove.sort(reverse=True)  # Delete from highest index down

        canvas.pushUndo("Delete Layer")

        for index in indexes2Remove:
            if 0 <= index < len(canvas.layers):
                layer = canvas.layers[index]
                # Remove from scene
                if layer.graphicsItem:
                    canvas.customScene.removeItem(layer.graphicsItem)
                canvas.layers.pop(index)

        # Reassign current layer safely
        if canvas.layers:
            canvas.currentLayer = canvas.layers[0]
        else:
            canvas.currentLayer = None

        self.updateLayerList()
        canvas.updateLayerOrder()
        canvas.viewport().update()

    def changeLayerOpacity(self, value):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return

        layer = canvas.currentLayer
        layer.opacity = value
        layer.updatePixmap()
        canvas.viewport().update()
    
    def changeLayerBlendMode(self, mode):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return

        canvas.currentLayer.blendMode = mode
        canvas.updateLayerOrder()

    def onLayersReordered(self, parent, start, end, destination, row):
        canvas = self.currentCanvas()
        if not canvas:
            return
        newOrder = []
        for i in range(self.layerList.count()):
            name = self.layerList.item(i).text()
            for layer in canvas.layers:
                if layer.name == name:
                    newOrder.append(layer)
                    break
        canvas.layers = newOrder
        canvas.updateLayerOrder()

    def onLayerSelectionChanged(self, currentRow):
        canvas = self.currentCanvas()
        if canvas and 0 <= currentRow < len(canvas.layers):
            canvas.currentLayer = canvas.layers[currentRow]
            self.updateOpacitySlider()
            self.blendModeDropdown.blockSignals(True)
            self.blendModeDropdown.setCurrentText(canvas.currentLayer.blendMode)
            self.blendModeDropdown.blockSignals(False)
            

    def updateOpacitySlider(self):
        canvas = self.currentCanvas()
        if canvas and canvas.currentLayer:
            self.layerOpacitySlider.blockSignals(True)
            self.layerOpacitySlider.setValue(canvas.currentLayer.opacity)
            self.layerOpacitySlider.blockSignals(False)


    def SaveLayerSelection(self):
        canvas = self.currentCanvas()
        if not canvas:
            return
        canvas.selectedLayerNames = {item.text() for item in self.layerList.selectedItems()}
    def toggleClippingMask(self):
        currentCanvas = self.currentCanvas()
        if not currentCanvas or not currentCanvas.currentLayer:
            QMessageBox.warning(self, "No Layer Selected", "Please select a layer first.")
            return

        layers = currentCanvas.layers
        clipIndex = layers.index(currentCanvas.currentLayer)

        if clipIndex == 0:
            QMessageBox.information(self, "No Layer Below", "Cannot apply clipping mask — no layer below.")
            return

        layer = currentCanvas.currentLayer
        layer.clippingMaskEnabled = not layer.clippingMaskEnabled

        status = "enabled" if layer.clippingMaskEnabled else "disabled"
        QMessageBox.information(self, "Clipping Mask", f"Clipping mask {status} for layer: {layer.name}")

    def toggleGrid(self):
        self.globalGridEnabled = self.toggleGridAction.isChecked()
        for i in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(i)
            if hasattr(tab, "canvas"):
                tab.canvas.toggleGrid(self.globalGridEnabled)

    def toggleRuler(self):
        self.globalRulerEnabled = self.toggleRulerAction.isChecked()
        for i in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(i)
            if hasattr(tab, "canvas"):
                tab.canvas.toggleRuler(self.globalRulerEnabled)

    def undoUI(self):
        canvas = self.currentCanvas()
        if canvas:
            canvas.undo()
            self.updateLayerList() 

    def redoUI(self):
        canvas = self.currentCanvas()
        if canvas:
            canvas.redo()
            self.updateLayerList()
    
    def updateEraserSize(self, value):
        print(f"[DEBUG] New eraser size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.eraserWidth = value
            canvas.updateEraser()


    def updateBrushSize(self, value):
        print(f"[DEBUG] New brush size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.penWidth = value
            canvas.updateBrush()
    
    def updateBrushOpacity(self, value):
        print(f"[DEBUG] New brush opacity size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.brushOpacity = value
            canvas.penColour = (*canvas.penColour[:3], value)
            canvas.updateBrush()

    def updateBrushSpacing(self, value):
        print(f"[DEBUG] New eraser opacity size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.eraserOpacity = value
            canvas.updateEraser()

    def updateBrushSpacing(self, value):
        print(f"[DEBUG] New brush: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.brushSpacing = value

    def updateEraserSpacing(self, value):
        print(f"[DEBUG] New brush: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.eraserSpacing = value

    def updatePencilSize(self, value):
        print(f"[DEBUG] New pencil size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.pencilWidth = value
            canvas.updatePencil()
    
    def updatePencilOpacity(self, value):
        print(f"[DEBUG] New pencil opacity size: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.pencilOpacity = value
            canvas.penColour = (*canvas.penColour[:3], value)
            canvas.updatePencil()

    def updatePencilSpacing(self, value):
        print(f"[DEBUG] New pencil spacing: {value}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.pencilSpacing = value
    
    def togglePencilMode(self):
        canvas = self.currentCanvas()
        if canvas:
            canvas.pencilMode = "erase" if canvas.pencilMode == "draw" else "draw"
            self.pencil_options.toggle_btn.setText("Switch to Draw" if canvas.pencilMode == "erase" else "Switch to Erase")
            canvas.updatePencil()

    def populateBrushes(self, combo_box):
        import os
        brushDirectory = "brushes"
        if not os.path.isdir(brushDirectory):
            return

        for filename in os.listdir(brushDirectory):
            if filename.lower().endswith((".png", ".jpg", ".bmp")):
                combo_box.addItem(filename)

    def onBrushImageChanged(self, name):
        print(f"[DEBUG] New brush: {name}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.loadBrushImage(os.path.join("brushes", name))

    def onEraserImageChanged(self, name):
        print(f"[DEBUG] New eraser: {name}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.loadEraserImage(os.path.join("brushes", name))

    def onPencilImageChanged(self, name):
        print(f"[DEBUG] New brush: {name}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.loadPencilImage(os.path.join("pencil", name))

    def setSelectionTool(self, mode):
        print(f"[DEBUG] New selection tool: {mode}")
        canvas = self.currentCanvas()
        if canvas:
            canvas.selectionTool = mode

    def clearSelection(self):
        canvas = self.currentCanvas()
        if canvas:
            canvas.clearSelection()

    def selectByColour(self):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return

        initial = self.selection_options.selectedColour
        picked = QColorDialog.getColor(initial, self, "Select Colour to Select From Canvas")

        if picked.isValid():
            self.selection_options.selectedColour = picked
            rgba = picked.getRgb()  # returns (r, g, b, a, _)
            targetColour = rgba[:4]
            canvas.selectAllColour(targetColour)

    def copySelection(self):
        canvas = self.currentCanvas()
        if not canvas or not canvas.selectionMask or not canvas.currentLayer:
            print("No selection to copy.")
            return

        layer = canvas.currentLayer
        mask = canvas.selectionMask
        source = layer.pil_image.copy()

        # Apply the mask to isolate selected pixels
        blank = Image.new("RGBA", source.size, (0, 0, 0, 0))
        self.selectionClipboard = Image.composite(source, blank, mask)
        print("Selection copied.")

    def cutSelection(self):
        self.copySelection()
        canvas = self.currentCanvas()
        if not canvas or not canvas.selectionMask or not canvas.currentLayer:
            return

        layer = canvas.currentLayer
        r, g, b, a = layer.pil_image.split()
        newAlpha = ImageChops.subtract(a, canvas.selectionMask)
        layer.pil_image = Image.merge("RGBA", (r, g, b, newAlpha))
        layer.updatePixmap()
        canvas.viewport().update()
        print("Selection cut.")
        
    def pasteClipboard(self):
        canvas = self.currentCanvas()
        if not canvas or self.selectionClipboard is None:
            print("Nothing to paste.")
            return

        img = self.selectionClipboard.copy()
        name = generateLayerName([layer.name for layer in canvas.layers])

        newLayer = Layer(name, Image.new("RGBA", (canvas.sceneWidth, canvas.sceneHeight), (0, 0, 0, 0)))
        newLayer.pil_image.paste(img, (0, 0))  # Paste at top-left for now

        canvas.addLayer(newLayer)
        canvas.currentLayer = newLayer
        canvas.viewport().update()
        print("Selection pasted as new layer.")

    def flipHorizontal(self):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return
        canvas.pushUndo("Flip Horizontal")

        img = canvas.currentLayer.pil_image
        if canvas.selectionMask:
            mask = canvas.selectionMask
            region = Image.composite(img, Image.new("RGBA", img.size, (0,0,0,0)), mask)
            region = region.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            canvas.currentLayer.pil_image.paste(region, (0, 0), mask)
        else:
            canvas.currentLayer.pil_image = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        canvas.currentLayer.updatePixmap()
        canvas.viewport().update()

    def flipVertical(self):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return
        canvas.pushUndo("Flip Vertical")

        img = canvas.currentLayer.pil_image
        if canvas.selectionMask:
            mask = canvas.selectionMask
            region = Image.composite(img, Image.new("RGBA", img.size, (0,0,0,0)), mask)
            region = region.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            canvas.currentLayer.pil_image.paste(region, (0, 0), mask)
        else:
            canvas.currentLayer.pil_image = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        canvas.currentLayer.updatePixmap()
        canvas.viewport().update()
    

    def showShearDialog(self):
        self.shearDialog = QDialog(self)
        self.shearDialog.setWindowTitle("Shear Image")

        layout = QVBoxLayout()

        self.shearXVal = QLineEdit()
        self.shearXVal.setPlaceholderText("Shear X (e.g. 0.5 or -1.2)")
        self.shearYVal = QLineEdit()
        self.shearYVal.setPlaceholderText("Shear Y (e.g. 0.0)")

        layout.addWidget(QLabel("Shear X:"))
        layout.addWidget(self.shearXVal)
        layout.addWidget(QLabel("Shear Y:"))
        layout.addWidget(self.shearYVal)

        shearButtonBox = QHBoxLayout()
        applyShearBtn = QPushButton("Apply")
        cancelShearBtn = QPushButton("Cancel")
        shearButtonBox.addWidget(applyShearBtn)
        shearButtonBox.addWidget(cancelShearBtn)
        layout.addLayout(shearButtonBox)

        applyShearBtn.clicked.connect(self.shearApplyButton)
        cancelShearBtn.clicked.connect(self.shearDialog.reject)

        self.shearDialog.setLayout(layout)
        self.shearDialog.exec()

    def shearApplyButton(self):
        try:
            xVal = float(self.shearXVal.text())
            yVal = float(self.shearYVal.text())

            # Bounds to stop lag
            xVal = max(-5.0, min(5.0, xVal))
            yVal = max(-5.0, min(5.0, yVal))

            self.shearDialog.accept()
            self.applyShear(xVal, yVal)
        except ValueError:
            self.shearXVal.setText("")
            self.shearYVal.setText("")
            self.shearXVal.setPlaceholderText("Invalid input")
            self.shearYVal.setPlaceholderText("Invalid input")

    def applyShear(self, xShear, yShear):
        canvas = self.currentCanvas()
        if not canvas or not canvas.currentLayer:
            return

        canvas.pushUndo("Shear Transform")

        img = canvas.currentLayer.pil_image
        mask = canvas.selectionMask

        if mask:
            region = Image.composite(img, Image.new("RGBA", img.size, (0,0,0,0)), mask)
            bbox = mask.getbbox()
        else:
            region = img
            bbox = region.getbbox()

        if bbox is None:
            print("Nothing to shear.")
            return

        region = region.crop(bbox)
        width, height = region.size

        shearMatrix = (1, xShear, 0, yShear, 1, 0)

        sheared = region.transform(
            (int(width + abs(xShear) * height), int(height + abs(yShear) * width)), Image.Transform.AFFINE, shearMatrix, resample=Image.LANCZOS)

        # Clear the original region (using a cropped transparent mask)
        output = img.copy()
        if mask:
            # Clear original selected area
            cropMask = mask.crop(bbox)
            output.paste(Image.new("RGBA", cropMask.size, (0, 0, 0, 0)), bbox, cropMask)
        else:
            # Clear the entire bounding box area
            clearBox = Image.new("RGBA", (bbox[2]-bbox[0], bbox[3]-bbox[1]), (0, 0, 0, 0))
            output.paste(clearBox, (bbox[0], bbox[1]))

        # Paste the sheared result
        output.paste(sheared, (bbox[0], bbox[1]), sheared)

        canvas.currentLayer.pil_image = output
        canvas.currentLayer.updatePixmap()
        canvas.viewport().update()

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    startup = StartupDialog()
    if startup.exec() == QDialog.DialogCode.Accepted:
        data = startup.getData()
        if data[0] == "custom":
            canvasWidth, canvasHeight = data[1], data[2]
            bgImg = None
        elif data[0] == "image":
            try:
                bgImg = Image.open(data[1]).convert("RGBA")
                canvasWidth, canvasHeight = bgImg.size
            except Exception as e:
                print(f"Error loading image: {e}")
                canvasWidth, canvasHeight = 2000, 2000
                bgImg = None
    else:
        sys.exit()

    window = MainWindow(canvasWidth=canvasWidth, canvasHeight=canvasHeight, bgImg=bgImg)
    window.show()
    sys.exit(app.exec())
    