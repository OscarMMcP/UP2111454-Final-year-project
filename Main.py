import sys
import os
import math
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QToolBar, QDockWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QListWidget, QColorDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QDialog, QLabel, QSlider, QStackedWidget, QTabWidget, QComboBox, QMessageBox
)
from PyQt6.QtGui import QAction, QActionGroup, QPixmap, QMouseEvent, QPen, QPainter, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PIL import Image, ImageQt, ImageDraw, ImageChops


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
    def __init__(self, name, pilImg):
        self.name = name
        self.pilImg = pilImg
        self.qtPixmap = QPixmap.fromImage(ImageQt.ImageQt(pilImg))
        self.graphicsItem = None  # To be set when added to the canvas

    def updatePixmap(self):
        self.qtPixmap = QPixmap.fromImage(ImageQt.ImageQt(self.pilImg))
        if self.graphicsItem:
            self.graphicsItem.setPixmap(self.qtPixmap)

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
        margin = max(self.sceneWidth, self.sceneHeight) // 2
        self.customScene.setSceneRect(
            -margin, -margin,
            self.sceneWidth + margin * 2,
            self.sceneHeight + margin * 2
        )

        self.setScene(self.customScene)

        self.layers = []
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
        

        self.drawing = False
        self.lastPoint = None
        self.lastStampPos = None
        self.strokeBuffer = None

        self.zoomFactor = 1.0
        self.currentZoom = 100
        self.moveLastMousePos = None
        self.currentScrollPos = QPointF(0, 0)

        self.undoStack = []  # List of tuples: (description, full_layer_state)
        self.redoStack = []

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self.shapeStartPoint = None
        self.shapePreviewBuffer = None

        self.loadBrushImage("brushes/01.png")
        self.loadEraserImage("brushes/01.png")

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

    def addLayer(self, layer):
        """
        adds a layer to the canvas
        """
        self.layers.append(layer)
        item = QGraphicsPixmapItem(layer.qtPixmap)
        item.setZValue(len(self.layers))
        self.customScene.addItem(item)
        layer.graphicsItem = item

        if len(self.layers) == 1:
            self.centerOn(item)
            self.currentScrollPos = self.mapToScene(self.viewport().rect().center())

    def updateLayerOrder(self):
        """
        Updates the ordering of the canvas in the image
        """
        for layerDepth, layer in enumerate(self.layers):
            if layer.graphicsItem:
                layer.graphicsItem.setZValue(layerDepth)

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

        if self.currentTool in ("paintbrush", "eraser") and event.button() == Qt.MouseButton.LeftButton and self.currentLayer:
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
            self.shapePreviewBuffer = self.currentLayer.pilImg.copy()
            event.accept()
            return

        super().mousePressEvent(event)

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

        if self.currentTool in ("paintbrush", "eraser") and self.drawing and self.currentLayer:
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
            self.currentLayer.pilImg = self.shapePreviewBuffer.copy()

            draw = ImageDraw.Draw(self.currentLayer.pilImg, "RGBA")
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

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Mouse button released
        """
        if self.currentTool == "move" and event.button() == Qt.MouseButton.LeftButton:
            self.moveLastMousePos = None
            event.accept()
            return

        if self.currentTool in ("paintbrush", "eraser") and self.drawing and event.button() == Qt.MouseButton.LeftButton:
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
        
        super().mouseReleaseEvent(event)

    def stampBrush(self, x, y):
        """
        Brush/ eraser stamping logic
        """
        if not self.currentLayer:
            return

        if self.currentTool == "eraser" and self.eraserImage:
            bx, by = self.eraserImage.size
            px = x - bx // 2
            py = y - by // 2

            base = self.currentLayer.pilImg.crop((px, py, px + bx, py + by)).copy()
            eraser_alpha = self.eraserImage.getchannel("A")
            mask = Image.new("L", (bx, by), 255)
            mask.paste(eraser_alpha, (0, 0))
            r, g, b, a = base.split()
            a = ImageChops.subtract(a, eraser_alpha)
            base = Image.merge("RGBA", (r, g, b, a))
            self.currentLayer.pilImg.paste(base, (px, py))

        elif self.currentTool == "paintbrush" and self.brushImage:
            bx, by = self.brushImage.size
            px = x - bx // 2
            py = y - by // 2
            region = self.currentLayer.pilImg.crop((px, py, px + bx, py + by))
            blended = Image.alpha_composite(region, self.brushImage)
            self.currentLayer.pilImg.paste(blended, (px, py))


    def floodFill(self, x, y, fillColour, tolerance=20):
        """
        Fills all neighboring pixels within a given color tolerance.
        """
        img = self.currentLayer.pilImg
        pixels = img.load()
        width, height = img.size
        targetColour = pixels[x, y]

        if targetColour == fillColour:
            return

        def withinBounds(nx, ny):
            return 0 <= nx < width and 0 <= ny < height

        def colourMatch(c1, c2):
            return all(abs(a - b) <= tolerance for a, b in zip(c1, c2))

        queue = [(x, y)]
        visited = set()
        visited.add((x, y))

        while queue:
            cx, cy = queue.pop(0)  # slow for large fills, but works fine
            if not withinBounds(cx, cy):
                continue
            if not colourMatch(pixels[cx, cy], targetColour):
                continue

            pixels[cx, cy] = fillColour

            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                nx, ny = cx + dx, cy + dy
                if withinBounds(nx, ny) and (nx, ny) not in visited:
                    queue.append((nx, ny))
                    visited.add((nx, ny))

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
        return [(layer.name, layer.pilImg.copy()) for layer in self.layers]

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

class MoveOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Move Tool - drag the canvas around"))

class FillOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Fill Tool (No options yet)"))

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
        layout.addWidget(QLabel("Transform Tool (No options yet)"))

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self, canvasWidth=2000, canvasHeight=2000, bgImg=None):
        super().__init__()
        self.setWindowTitle("Iteration 2")
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

        # Dock widget for colour picker and layer list.
        self.createRightDock()

        # Top toolbar for tool-specific options.
        self.toolOptionsStack = QStackedWidget(self)
        self.paintbrush_options = PaintbrushOptions(self)
        self.eraser_options = EraserOptions(self)
        self.move_options = MoveOptions(self)
        self.fill_options = FillOptions(self)
        self.shape_options = ShapeOptions(self)
        self.transform_options = TransformOptions(self)

        self.toolOptionsStack.addWidget(self.paintbrush_options)
        self.paintbrush_options.brushSizeSlider.valueChanged.connect(self.updateBrushSize)
        self.paintbrush_options.brushOpacitySlider.valueChanged.connect(self.updateBrushOpacity)
        self.populate_brush_selector(self.paintbrush_options.brushSelector)
        self.paintbrush_options.brushSelector.currentTextChanged.connect(self.onBrushImageChanged)
        self.paintbrush_options.brushSpacingSlider.valueChanged.connect(self.updateBrushSpacing)

        self.toolOptionsStack.addWidget(self.eraser_options)
        self.eraser_options.eraserSizeSlider.valueChanged.connect(self.updateEraserSize)
        self.eraser_options.eraserOpacitySlider.valueChanged.connect(self.updateEraserOpactity)
        self.populate_brush_selector(self.eraser_options.eraserSelector)
        self.eraser_options.eraserSelector.currentTextChanged.connect(self.onEraserImageChanged)
        self.eraser_options.eraserOpacitySlider.valueChanged.connect(self.updateEraserSpacing)

        self.toolOptionsStack.addWidget(self.move_options)

        self.toolOptionsStack.addWidget(self.fill_options)

        self.toolOptionsStack.addWidget(self.shape_options)

        self.toolOptionsStack.addWidget(self.transform_options)

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
        undoAction.triggered.connect(self.undoUI)
        redoAction.triggered.connect(self.redoUI)
        editMenu.addAction(undoAction)
        editMenu.addAction(redoAction)

        view_menu = menubar.addMenu("View")
        self.toggleGridAction = QAction("Show Grid", self, checkable=True)
        self.toggleGridAction.setChecked(False)
        self.toggleGridAction.triggered.connect(self.toggleGrid)
        view_menu.addAction(self.toggleGridAction)

        self.toggleRulerAction = QAction("Show Ruler", self, checkable=True)
        self.toggleRulerAction.setChecked(False)
        self.toggleRulerAction.triggered.connect(self.toggleRuler)
        view_menu.addAction(self.toggleRulerAction)

    def createRightDock(self):
        self.rightDock = QDockWidget("Colour & Layers", self)
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
        # Global layer list; its content is updated when the tab changes.
        self.layerList = QListWidget()
        self.layerList.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.layerList.model().rowsMoved.connect(self.onLayersReordered)
        self.layerList.currentRowChanged.connect(self.onLayerSelectionChanged)
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
        # Clear and update the layer list with layers from the current canvas.
        self.layerList.clear()
        canvas = self.currentCanvas()
        if canvas:
            for layer in canvas.layers:
                self.layerList.addItem(layer.name)
            self.layerList.setCurrentRow(0)

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
                finalImage.paste(layer.pilImg, (0, 0), layer.pilImg)
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
                finalImage.paste(layer.pilImg, (0, 0), layer.pilImg)

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
                layer.pilImg.save(path)
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
        elif toolName == "move":
            self.toolOptionsStack.setCurrentWidget(self.move_options)
        elif toolName == "fill":
            self.toolOptionsStack.setCurrentWidget(self.fill_options)
        elif toolName == "shape":
            self.toolOptionsStack.setCurrentWidget(self.shape_options)
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
        image = Image.new("RGBA", (cw, ch), (255, 255, 255, 0))
        layerName = f"Layer {len(canvas.layers) + 1}"
        layer = Layer(layerName, image)
        canvas.addLayer(layer)
        self.updateLayerList()

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

    def updateEraserOpactity(self, value):
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

    def populate_brush_selector(self, combo_box):
        import os
        brush_dir = "brushes"
        if not os.path.isdir(brush_dir):
            return

        for filename in os.listdir(brush_dir):
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
    