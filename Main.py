import sys
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenuBar, QToolBar, QDockWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QListWidget, QColorDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QDialog, QLabel, QSlider, QStackedWidget, QTabWidget
)
from PyQt6.QtGui import QAction, QActionGroup, QPixmap, QMouseEvent, QPen, QPainter, QFont
from PyQt6.QtCore import Qt, QRectF
from PIL import Image, ImageQt, ImageDraw

# --- Startup Dialog ---
class StartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Canvas Size")
        self.imagePath = None

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

        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if fileName:
            self.imagePath = fileName  # Ensure it's a valid file path
            try:
                with Image.open(self.imagePath) as img:
                    width, height = img.size
                self.widthEdit.setText(str(width))
                self.heightEdit.setText(str(height))
                self.accept()  # Accept the dialog
            except Exception as e:
                self.accept()  # Accept the dialog even if there was an error
                return(f"Error loading image: {e}")
                

    def getData(self):
        """
        Returns the selected data (custom dimensions or image path).
        """
        if self.imagePath:
            return ("image", self.imagePath)
        try:
            width = int(self.widthEdit.text())
            height = int(self.heightEdit.text())
        except ValueError:
            width, height = 2000, 2000
        return ("custom", width, height)


# --- Custom Scene for Grid and Rulers ---
class CustomScene(QGraphicsScene):
    def __init__(self, gridEnabled=False, rulerEnabled=False, gridSpacing=1, rulerSpacing=100, parent=None):
        super().__init__(parent)
        self.gridEnabled = gridEnabled
        self.rulerEnabled = rulerEnabled
        self.gridSpacing = gridSpacing
        self.rulerSpacing = rulerSpacing

    def drawForeground(self, painter: QPainter, rect: QRectF):
        # Draw Grid
        if self.gridEnabled:
            pen = QPen(Qt.GlobalColor.lightGray)
            pen.setWidth(0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            left = math.floor(rect.left() / self.gridSpacing) * self.gridSpacing
            top = math.floor(rect.top() / self.gridSpacing) * self.gridSpacing
            x = left
            while x < rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
                x += self.gridSpacing
            y = top
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += self.gridSpacing

        # Draw Ruler
        if self.rulerEnabled:
            pen = QPen(Qt.GlobalColor.darkGray)
            pen.setWidth(0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            font = QFont("Arial", 8)
            painter.setFont(font)
            step = self.rulerSpacing
            start_x = math.floor(rect.left() / step) * step
            if start_x < rect.left():
                start_x += step
            x = start_x
            while x < rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.top()) + 10)
                painter.drawText(int(x) + 2, int(rect.top()) + 10, str(int(x)))
                x += step

            start_y = math.floor(rect.top() / step) * step
            if start_y < rect.top():
                start_y += step
            y = start_y
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.left()) + 10, int(y))
                painter.drawText(int(rect.left()) + 12, int(y) + 4, str(int(y)))
                y += step


# --- Layer Class ---
class Layer:
    def __init__(self, name, pilImg):
        self.name = name
        self.pilImg = pilImg
        self.qtPixmap = QPixmap.fromImage(ImageQt.ImageQt(pilImg))
        self.graphicsItem = None  # To be set when added to the canvas

    def updatePixmap(self):
        self.qtPixmap = QPixmap.fromImage(ImageQt.ImageQt(self.pilImg))
        if self.graphicsItem:
            self.graphicsItem.setPixmap(self.qtPixmap)

# --- Canvas Class ---
class Canvas(QGraphicsView):
    def __init__(self, sceneWidth=2000, sceneHeight=2000, gridEnabled=False, rulerEnabled=False, parent=None):
        super().__init__(parent)
        self.sceneWidth = sceneWidth
        self.sceneHeight = sceneHeight
        self.customScene = CustomScene(gridEnabled, rulerEnabled, gridSpacing=1,rulerSpacing=100)
        self.customScene.setSceneRect(0, 0, self.sceneWidth, self.sceneHeight)
        self.setScene(self.customScene)

        # general intialisation
        self.layers = []
        self.currentTool = "paintbrush" 
        self.penColour = (0, 0, 0, 255)
        self.penWidth = 100
        self.drawing = False
        self.lastPoint = None
        self.currentLayer = None
        self.currentZoom = 100

    def addLayer(self, layer):
        self.layers.append(layer)
        item = QGraphicsPixmapItem(layer.qtPixmap)
        item.setZValue(len(self.layers))
        self.customScene.addItem(item)
        layer.graphicsItem = item

    def updateLayerOrder(self):
        for idx, layer in enumerate(self.layers):
            if layer.graphicsItem:
                layer.graphicsItem.setZValue(idx)

    def clearLayers(self):
        self.customScene.clear()
        self.layers = []

    def drawDot(self, point):
        if self.currentLayer is None:
            return
        draw = ImageDraw.Draw(self.currentLayer.pilImg)
        r = self.penWidth // 2
        fill = (0, 0, 0, 0) if self.currentTool == "eraser" else self.penColour
        bbox = [point[0]-r, point[1]-r, point[0]+r, point[1]+r]
        draw.ellipse(bbox, fill=fill)
        self.currentLayer.updatePixmap()

    def mousePressEvent(self, event: QMouseEvent):
        if self.currentTool == "move":
            super().mousePressEvent(event)
            return

        if self.currentLayer is None:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            scenePos = self.mapToScene(event.position().toPoint())
            point = (int(scenePos.x()), int(scenePos.y()))
            self.lastPoint = point
            if self.currentTool in ("paintbrush", "eraser"):
                self.drawDot(point)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drawing and self.currentLayer:
            scenePos = self.mapToScene(event.position().toPoint())
            currentPoint = (int(scenePos.x()), int(scenePos.y()))
            draw = ImageDraw.Draw(self.currentLayer.pilImg)
            if self.lastPoint:
                distance = math.dist(self.lastPoint, currentPoint)
                numPoints = max(int(distance / 4), 1)
                for i in range(numPoints + 1):
                    x = int(self.lastPoint[0] + (currentPoint[0] - self.lastPoint[0]) * (i / numPoints))
                    y = int(self.lastPoint[1] + (currentPoint[1] - self.lastPoint[1]) * (i / numPoints))
                    bbox = (x - self.penWidth // 2, y - self.penWidth // 2,
                            x + self.penWidth // 2, y + self.penWidth // 2)
                    draw.ellipse(bbox, fill=self.penColour if self.currentTool == "paintbrush" else (0, 0, 0, 0))
            # If eraser is selected, use transparent fill, else use pen colour
            draw.line([self.lastPoint, currentPoint], fill=self.penColour if self.currentTool == "paintbrush" else (0, 0, 0, 0), width=self.penWidth, joint='curve')
            self.lastPoint = currentPoint
            self.currentLayer.updatePixmap()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.drawing and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.lastPoint = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Zoom with Ctrl+mouse wheel
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() // 120
            try:
                zoom = int(self.currentZoom)
            except ValueError:
                zoom = 100
            zoom += delta * 10
            zoom = max(10, zoom)
            self.currentZoom = zoom
            self.setZoom(zoom)
        else:
            super().wheelEvent(event)

    def setZoom(self, zoomPercent):
        self.currentZoom = zoomPercent
        factor = zoomPercent / 100.0
        self.resetTransform()
        self.scale(factor, factor)

    def setTool(self, toolName, colour=None):
        self.currentTool = toolName
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if toolName == "move" else QGraphicsView.DragMode.NoDrag)
        if toolName == "paintbrush" and colour is not None:
            self.penColour = colour

    def toggleGrid(self, enabled: bool):
        self.customScene.gridEnabled = enabled
        self.customScene.update()

    def toggleRuler(self, enabled: bool):
        self.customScene.rulerEnabled = enabled
        self.customScene.update()

# --- CanvasTabWidget: Contains a Canvas and its own zoom controls ---
class CanvasTabWidget(QWidget):
    def __init__(self, canvasWidth, canvasHeight, gridEnabled, rulerEnabled, bgImage=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # Create the canvas.
        self.canvas = Canvas(sceneWidth=canvasWidth, sceneHeight=canvasHeight,
                             gridEnabled=gridEnabled, rulerEnabled=rulerEnabled)
        # Add a background layer.
        if bgImage:
            bgImage = bgImage.resize((canvasWidth, canvasHeight))
        else:
            bgImage = Image.new("RGBA", (canvasWidth, canvasHeight), (255, 255, 255, 255))
        layer = Layer("Layer 1", bgImage)
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
            zoom = int(self.zoomEdit.text())
        except ValueError:
            zoom = 100
            self.zoomEdit.setText(str(zoom))
        self.canvas.setZoom(zoom)

# --- Tool Option Panels ---
class PaintbrushOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paintbrush Options:"))
        self.brushSize = QSlider(Qt.Orientation.Horizontal)
        self.brushSize.setMinimum(1)
        self.brushSize.setMaximum(50)
        self.brushSize.setValue(5)
        layout.addWidget(self.brushSize)

class EraserOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Eraser Options:"))
        self.eraserSize = QSlider(Qt.Orientation.Horizontal)
        self.eraserSize.setMinimum(1)
        self.eraserSize.setMaximum(50)
        self.eraserSize.setValue(5)
        layout.addWidget(self.eraserSize)

class MoveOptions(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Move Tool (No options yet)"))

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self, canvasWidth=2000, canvasHeight=2000, bgImage=None):
        super().__init__()
        self.setWindowTitle("Iteration 1")
        self.resize(2000, 1200)

        # Central tab widget holds multiple canvas tabs.
        self.tabWidget = QTabWidget(self)
        self.setCentralWidget(self.tabWidget)
        self.tabWidget.currentChanged.connect(self.updateLayerList)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)

        # Menus.
        self.createMenus()

        # Dock widget for colour picker and layer list.
        self.createRightDock()

        # Top toolbar for tool-specific options.
        self.toolOptionsStack = QStackedWidget(self)
        self.paintbrushOptions = PaintbrushOptions(self)
        self.eraserOptions = EraserOptions(self)
        self.moveOptions = MoveOptions(self)
        self.toolOptionsStack.addWidget(self.paintbrushOptions)
        self.toolOptionsStack.addWidget(self.eraserOptions)
        self.toolOptionsStack.addWidget(self.moveOptions)
        self.toolOptionsToolBar = QToolBar("Tool Options", self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolOptionsToolBar)
        self.toolOptionsToolBar.addWidget(self.toolOptionsStack)
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
        
        self.eraserAction = QAction("Eraser", self, checkable=True)
        self.eraserAction.triggered.connect(lambda: self.selectTool("eraser"))
        self.toolsToolBar.addAction(self.eraserAction)
        self.toolGroup.addAction(self.eraserAction)
        
        self.moveAction = QAction("Move", self, checkable=True)
        self.moveAction.triggered.connect(lambda: self.selectTool("move"))
        self.toolsToolBar.addAction(self.moveAction)
        self.toolGroup.addAction(self.moveAction)
        
        self.paintbrushAction.setChecked(True)
        self.currentTool = "paintbrush"

        # Add the initial canvas tab.
        self.addNewCanvas(canvasWidth, canvasHeight, bgImage)

    def createMenus(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("File")
        newTabAction = QAction("New...", self)
        newTabAction.triggered.connect(self.newTab)
        fileMenu.addAction(newTabAction)
        
        openAction = QAction("Open Image as Layer...", self)
        openAction.triggered.connect(self.openFile)
        fileMenu.addAction(openAction)

        saveAction = QAction("Save Image", self)
        saveAction.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAction)
        fileMenu.addSeparator()
        exitAction = QAction("Exit", self)
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        editMenu = menubar.addMenu("Edit")
        editMenu.addAction("Undo")
        editMenu.addAction("Redo")

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
        self.rightDock = QDockWidget("Colour & Layers", self)
        self.rightDock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.rightDock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures | QDockWidget.DockWidgetFeature.DockWidgetMovable)
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

    def addNewCanvas(self, canvasWidth, canvasHeight, bgImage=None):
        # Create a new CanvasTabWidget instance.
        tab = CanvasTabWidget(canvasWidth, canvasHeight,
                              gridEnabled=self.toggleGridAction.isChecked(),
                              rulerEnabled=self.toggleRulerAction.isChecked(),
                              bgImage=bgImage)
        self.tabWidget.addTab(tab, f"Canvas {self.tabWidget.count()+1}")
        self.tabWidget.setCurrentWidget(tab)
        self.updateLayerList()

    def newTab(self):
        startup = StartupDialog()
        if startup.exec() == QDialog.DialogCode.Accepted:
            data = startup.getData()
            if data[0] == "custom":
                canvasWidth, canvasHeight = data[1], data[2]
                bgImage = None
            elif data[0] == "image":
                try:
                    bgImage = Image.open(data[1]).convert("RGBA")
                    canvasWidth, canvasHeight = bgImage.size
                except Exception as e:
                    print(f"Error loading image: {e}")
                    canvasWidth, canvasHeight = 2000, 2000
                    bgImage = None
            self.addNewCanvas(canvasWidth, canvasHeight, bgImage)

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
        canvas = self.currentCanvas()  # Get the current active canvas
        if not canvas:
            print("Error: No canvas available.")  # Ensure there is a canvas to save
            return
        
        # Open the file save dialog
        fileName, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;BMP Files (*.bmp)")

        if not fileName:
            print("Error: No file selected.")  # If no file is selected, return early
            return
        
        # Check if the file path is valid and doesn't start with data URL or unsupported schemes
        if fileName.startswith("data:"):
            print(f"Error: Invalid file scheme (data URL) - {fileName}")
            return
        
        # Ensure the file name ends with a valid extension
        if not fileName.lower().endswith(('.png', '.jpg', '.bmp')):
            print("Warning: File extension is not valid. Adding .png as default.")
            fileName += ".png"  # Add a .png extension if not already present
        
        try:
            width = canvas.sceneWidth
            height = canvas.sceneHeight
            finalImage = Image.new("RGBA", (width, height), (255, 255, 255, 255))  # Create a new image with white background
            
            # Paste each layer onto the final image
            for layer in canvas.layers:
                finalImage.paste(layer.pilImg, (0, 0), layer.pilImg)
            
            # Save the image to the specified file path
            finalImage.save(fileName)
            print(f"Image saved as {fileName}")  # Success message

        except Exception as e:
            print(f"Error saving image: {e}")  # Catch any errors during saving


    def openFile(self):
        canvas = self.currentCanvas()
        if not canvas:
            print("Error: No canvas available.")
            return
        
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.bmp)")
        if not fileName:
            return
        
        try:
            image = Image.open(fileName).convert("RGBA")
            cw, ch = canvas.sceneWidth, canvas.sceneHeight
            if image.width != cw or image.height != ch:
                newImage = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
                newImage.paste(image, ((cw - image.width) // 2, (ch - image.height) // 2))
                image = newImage
            layerName = f"Layer {len(canvas.layers) + 1}"
            layer = Layer(layerName, image)
            canvas.addLayer(layer)
            self.updateLayerList()
            canvas.currentLayer = canvas.layers[-1]
        except Exception as e:
            print(f"Error opening image: {e}")

    def selectTool(self, toolName):
        self.currentTool = toolName
        canvas = self.currentCanvas()
        if canvas:
            canvas.setTool(toolName, colour=canvas.penColour)
        if toolName == "paintbrush":
            self.toolOptionsStack.setCurrentWidget(self.paintbrushOptions)
        elif toolName == "eraser":
            self.toolOptionsStack.setCurrentWidget(self.eraserOptions)
        elif toolName == "move":
            self.toolOptionsStack.setCurrentWidget(self.moveOptions)
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
        canvas = self.currentCanvas()
        if canvas:
            canvas.toggleGrid(self.toggleGridAction.isChecked())

    def toggleRuler(self):
        canvas = self.currentCanvas()
        if canvas:
            canvas.toggleRuler(self.toggleRulerAction.isChecked())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    startup = StartupDialog()
    if startup.exec() == QDialog.DialogCode.Accepted:
        data = startup.getData()
        if data[0] == "custom":
            canvasWidth, canvasHeight = data[1], data[2]
            bgImage = None
        elif data[0] == "image":
            try:
                bgImage = Image.open(data[1]).convert("RGBA")
                canvasWidth, canvasHeight = bgImage.size
            except Exception as e:
                print(f"Error loading image: {e}")
                canvasWidth, canvasHeight = 2000, 2000
                bgImage = None
    else:
        sys.exit()

    window = MainWindow(canvasWidth=canvasWidth, canvasHeight=canvasHeight, bgImage=bgImage)
    window.show()
    sys.exit(app.exec())
