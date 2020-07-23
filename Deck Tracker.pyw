import requests
import json
import threading
import os.path
import sys
import platform
from tkinter import *
from tkinter import font
from fast_autocomplete import AutoComplete
import queue
from datetime import datetime

import psutil
import time
import data_updater as du
from PIL import Image, ImageFilter, ImageTk

#should move this to a constants file, I think
factionColors = {
                'IO': '#653475',
                'DE': '#c35242',
                'SI': '#122e39',
                'FR': '#0887d8',
                'NX': '#a51010',
                'PZ': '#ca872a'
}
log_dir = os.path.join(os.getcwd(), r'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log = open("logs/" + datetime.now().strftime("%Y%m%d%H%M%S") + ".txt", "w")
#sys.stdout = log

def apply_gradient(image, factionColor, gradient=3.0, initialOpacity=1.0):
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    width, height = image.size

    alpha_gradient = Image.new('L', (width, 1), color=0xFF)
    for x in range(width):
        a = int((initialOpacity * 255.) * (1. - gradient * float(x)/width))
        if a > 0:
            alpha_gradient.putpixel((x, 0), a)
        else:
            alpha_gradient.putpixel((x, 0), 0)
    alpha = alpha_gradient.resize(image.size)

    colorIm = Image.new('RGBA', image.size, color=factionColor)
    colorIm.putalpha(alpha)

    return Image.alpha_composite(image, colorIm)

def apply_shadow(image, shadow=0.9, shadowDepth=2):
    width, height = image.size
    pixels = image.load()
    for x in range(width):
        for y in range(shadowDepth):
            coordinate = x,y
            newPixels = []
            for i in image.getpixel(coordinate):
                newPixels.append(int(i*shadow))
            newValues = tuple(newPixels)
            pixels[x,y] = newValues
        for y in range(height-shadowDepth,height):
            coordinate = x,y
            newPixels = []
            for i in image.getpixel(coordinate):
                newPixels.append(int(i*shadow))
            newValues = tuple(newPixels)
            pixels[x,y] = newValues
    return  image

def alter_image(image, factionColor):
    width, height = image.size
    top = height/2 - width/10
    bottom = height/2 + width/10
    image = image.crop((0,top,width,bottom))
    image = image.resize((150, 30), Image.ANTIALIAS)
    image = apply_gradient(image, factionColor)
    return image

def create_background(rgbColor, width, height):
    background = Image.new('RGB', (width, height))
    pixels = background.load()
    for x in range(width):
        for y in range(height):
            pixels[x,y] = rgbColor
    return background

def concatenate_images(image1, image2):
    newImage = Image.new('RGB', (image1.width+image2.width, image1.height))
    newImage.paste(image1, (0,0))
    newImage.paste(image2, (image1.width, 0))
    return newImage

class Application(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()

        self.width = 270
        self.offset_x = 0
        self.offset_y = 0
        self.bind('<Button-1>', self.click_window)
        self.bind('<B1-Motion>', self.drag_window)        
        self.open_waiting_screen()
    
    def open_waiting_screen(self):
        root.overrideredirect(FALSE)
        root.title("RuneTracker - Currently waiting for game.")
        root.wm_attributes("-topmost", 0)
        self.frame = Frame(self, width=self.width, height=40, bd=1, bg="white")
        self.frame.pack()
        self.menu = Canvas(self.frame, width = self.width, height=40, highlightthickness=1, bd=0, bg="white")
        self.menu.pack()
        self.quitButton = Button(self.menu, command = self.master.destroy, highlightthickness=0, bd=0)
        self.menu.text = self.menu.create_text(135, 20, fill="black", text="Waiting for game to start", anchor = CENTER)


    def start_game(self):
        self.menu.pack_forget()
        self.menu.destroy()
        self.frame.pack_forget()
        self.frame.destroy()
        root.wm_attributes("-topmost", 1)
        root.overrideredirect(True)
        global dawg
        self.toggle = False
        self.cardList = dict()
        self.frameList = dict()
        self.create_widgets()
        self.autocomplete = AutoComplete(words=dawg)


    def end_game(self):
        self.menu.pack_forget()
        self.menu.destroy()
        self.frame.pack_forget()
        self.frame.destroy()
        for card in self.cardList:
            self.cardList[card].pack_forget()
            self.cardList[card].destroy()
            self.frameList[card].pack_forget()
            self.frameList[card].destroy()
        self.chanceWindow.pack_forget()
        self.chanceWindow.destroy()
        self.pack_forget()
        self.pack()

    def unload_preview(self):
        try:
            for result in self.search_preview:
                self.search_preview[result].canvas.pack_forget()
                self.search_preview[result].destroy()
        except AttributeError:
            return
    
    def unload_preview_event(self, event):
        self.unload_preview()

    def add_card_by_name(self, event, card_name):
        print(card_name)
        for card in parsedData:
            if(parsedData[card]['name'].lower() == card_name):
                self.add_cards([card])
                self.frameList[card].pack(side = "bottom")
                break

    def add_cards(self, cards):
        self.clear_recent()
        for card in cards:
            if(card in self.cardList.keys()):
                self.increment_card(self.cardList[card])
                return
            cardHeight = 30
            factionColor = factionColors[str(card)[2:4]]
            self.frameList[card] = Frame(self, width= self.width, height = cardHeight+2, bd=0 , highlightthickness=1, highlightbackground="black", bg="black")
            preview_str = "img/" + str(card) + ".png"

            try:
                locStr = "alt_img/" + str(card) + ".png"
                img = Image.open(locStr)
            except:
                fulStr = "img/" + str(card) + "-full.png"
                img = Image.open(fulStr)
                img = alter_image(img, factionColor)
                rgbColor = img.getpixel((0,0))
                backgroundImg = create_background(rgbColor, int(self.width/2), cardHeight)
                img = concatenate_images(backgroundImg, img)
                img = apply_shadow(img)
                img.save("alt_img/" + str(card) + ".png")

            full_pic = ImageTk.PhotoImage(Image.open(preview_str).resize((340, 520)))
            cardPic = ImageTk.PhotoImage(img)

            self.cardList[card] = Canvas(self.frameList[card], borderwidth=0, width=self.width, height=cardHeight, highlightthickness=0, bg=factionColor)
            self.cardList[card].create_image(0,0, image=cardPic, anchor=NW)
            self.cardList[card].cardPic = cardPic
            self.cardList[card].full_pic = full_pic
            try:
                self.cardList[card].count = du.decklist["CardsInDeck"][card]["Count"]
            except KeyError:
                self.cardList[card].count = 1
            self.total += self.cardList[card].count
            fontSize = 8
            fontName = "malgun gothic"
            fontStyle = "bold"
            self.cardList[card].recent = 1
            self.cardList[card].name_str = parsedData[card]["name"].upper()
            self.cardList[card].name = self.cardList[card].create_text(37, 16, fill="black", text=" ".join(self.cardList[card].name_str), font=(fontName,fontSize, fontStyle), anchor = W)
            self.cardList[card].name = self.cardList[card].create_text(36, 15, fill="white", text=" ".join(self.cardList[card].name_str), font=(fontName,fontSize, fontStyle), anchor = W)
            self.cardList[card].recent_text_shadow = self.cardList[card].create_text(250, 16, fill="black", text="+"+str(self.cardList[card].recent), font=(fontName,fontSize+4, fontStyle), anchor = E)
            self.cardList[card].recent_text = self.cardList[card].create_text(249, 15, fill="lime", text="+"+str(self.cardList[card].recent), font=(fontName,fontSize+4, fontStyle), anchor = E)
            self.chanceWindow = Canvas(self.cardList[card], width=31, height=cardHeight, highlightthickness=0, bg="#131621")
            self.cardList[card].create_window(0, 0, anchor=NW, window=self.chanceWindow)
            self.cardList[card].chanceWindow = self.chanceWindow
            position = (3,15)
            if self.toggle:
                displayValue = str(round(self.cardList[card].count*100/self.total, 1)) + "%"
                font_size = 8
            else:
                displayValue = " " + str(self.cardList[card].count) + "x"
                font_size = 11
            self.cardList[card].count_text=self.cardList[card].chanceWindow.create_text(position, fill="white",
                text = displayValue,
                font=("Helvetica",font_size,'roman'), anchor = W)
            self.cardList[card].pack(side = "bottom")

            self.cardList[card].bind("<Button-1>", lambda event, cardButton = self.cardList[card]: self.increment_card_by_click(event, cardButton))
            self.cardList[card].bind("<Button-3>", lambda event, cardButton = self.cardList[card]: self.decrement_card_by_click(event, cardButton))
            self.cardList[card].bind("<Enter>", lambda event, cardButton = self.cardList[card]: self.show_card(event, cardButton))
            self.cardList[card].bind("<Leave>", lambda event, cardButton = self.cardList[card]: self.hide_card(event, cardButton))


    def finish_word(self, event):
        self.unload_preview()
        if(type(event) == str):
            return

        x = self.search_bar.winfo_rootx()
        y = self.search_bar.winfo_rooty()
        if (event.char.isprintable()):
            input = self.search_bar.get() + event.char
        elif (event.keycode==8):
            input = self.search_bar.get()[:-1]
        else:
            return
        self.search_preview = {}
        results = self.autocomplete.search(word=input, max_cost = 2, size = 5)
        for result_int in range(len(results)):
            self.search_preview[result_int] = Toplevel()
            self.search_preview[result_int].overrideredirect(True)
            self.search_preview[result_int].wm_attributes("-topmost", 1)
            self.search_preview[result_int].geometry("125x20+" + str(x) + "+" + str(y +22 + 22*result_int))
            self.search_preview[result_int].canvas = Canvas(self.search_preview[result_int], width = 125, height = 20, borderwidth = 0, highlightthickness = 0)
            self.search_preview[result_int].text = self.search_preview[result_int].canvas.create_text(5, 5, text = results[result_int], anchor = NW)
            self.search_preview[result_int].canvas.bind('<Button-1>', lambda event, card_name = results[result_int]: self.add_card_by_name(event, card_name[0]))
            self.search_preview[result_int].canvas.pack()

    def click_window(self, event):
        self.offset_x = event.x
        self.offset_y = event.y
        self.unload_preview()
        
    def drag_window(self,event):
        x = self.master.winfo_pointerx() - self.offset_x
        y = self.master.winfo_pointery() - self.offset_y
        self.master.geometry('+{x}+{y}'.format(x=x,y=y))
        self.unload_preview()

    def create_widgets(self):
        self.create_menu()
        self.show_deck_list()

    def toggle_chance(self):
        self.toggle = not self.toggle
        self.update_counters()

    def create_menu(self):
        self.frame = Frame(self, width=self.width, height=40, bd=1, bg="black")
        self.frame.pack()

        self.menu = Canvas(self.frame, width = self.width, height=40, highlightthickness=1, bd=0, bg="#131621")
        self.menu.pack()
        self.toggleButton = Button(self.menu, command = self.toggle_chance, highlightthickness=0, bd=0)
        toggleLocStr = "menu_img/toggle_button.png"
        self.search_bar = Entry(self.menu)
        self.search_bar_window = self.menu.create_window(25,10, anchor=NW, window=self.search_bar)
        self.search_bar.bind('<Key>', self.finish_word)

        toggleImg = Image.open(toggleLocStr)
        togglePic = ImageTk.PhotoImage(toggleImg)
        self.toggleButton.configure(image=togglePic)
        self.toggleImg = togglePic
        self.toggleButtonWindow = self.menu.create_window(self.width-30,3, anchor=NE, window=self.toggleButton)
        self.quitButton = Button(self.menu, command = self.master.destroy, highlightthickness=0, bd=0)
        quitLocStr = "menu_img/quit_button.png"
        quitImg = Image.open(quitLocStr)
        quitPic = ImageTk.PhotoImage(quitImg)
        self.quitButton.configure(image=quitPic)
        self.quitImg = quitPic
        self.quitButtonWindow = self.menu.create_window(self.width,3, anchor=NE, window=self.quitButton)
        self.menu.bind('<Button-1>', self.click_window)
        self.menu.bind('<B1-Motion>', self.drag_window)

    def update_counters(self):
        for card in self.cardList:
            if self.toggle:
                displayValue = str(round(self.cardList[card].count*100/self.total,1)) + "%"
                font_size = 8
            else:
                displayValue = " " + str(self.cardList[card].count) + "x"
                font_size = 11
            if(self.cardList[card].recent == 0):
                self.cardList[card].itemconfigure(self.cardList[card].recent_text_shadow,
                    text="")
                self.cardList[card].itemconfigure(self.cardList[card].recent_text,
                    text="")
            elif(self.cardList[card].recent < 0):
                self.cardList[card].itemconfigure(self.cardList[card].recent_text_shadow,
                    text=str(self.cardList[card].recent))
                self.cardList[card].itemconfigure(self.cardList[card].recent_text,
                    text=str(self.cardList[card].recent))
            else:
                self.cardList[card].itemconfigure(self.cardList[card].recent_text_shadow,
                    text="+"+str(self.cardList[card].recent))
                self.cardList[card].itemconfigure(self.cardList[card].recent_text,
                    text="+"+str(self.cardList[card].recent))

            self.cardList[card].chanceWindow.itemconfigure(self.cardList[card].count_text,
                text=displayValue, font=("Helvetica",font_size,'roman'))

    def increment_card(self, cardButton):
        cardButton.count += 1
        self.total+= 1
        cardButton.recent += 1
        print(self.finish_word(cardButton.name_str))
        self.update_counters()

    def decrement_card(self, cardButton):
        if (cardButton.count == 0):
            return
        cardButton.count -= 1
        cardButton.recent -= 1
        self.total -= 1
        self.update_counters()

    def increment_card_by_click(self, event, cardButton):
        self.clear_recent()
        self.increment_card(cardButton)
    
    def decrement_card_by_click(self, event, cardButton):
        self.clear_recent()
        self.decrement_card(cardButton)

    def show_card(self, event, cardButton):
        x = root.winfo_pointerx()
        y = root.winfo_pointery()
        minHeight = root.winfo_screenheight() - 520
        if (minHeight < y): y=minHeight
        cardButton.preview = Toplevel()
        cardButton.preview.overrideredirect(True)
        cardButton.preview.wm_attributes("-topmost", 1)
        cardButton.preview.geometry("340x490+" + str(x+30) + "+" + str(y))
        cardButton.preview.canvas = Canvas(cardButton.preview, width=340, height=520, borderwidth=0, highlightthickness = 0)
        cardButton.preview.canvas.create_image(0, 0, anchor = NW, image = cardButton.full_pic)
        if(platform.system() == 'Windows'):
            transparent = "green"
            cardButton.preview.wm_attributes("-transparentcolor", transparent)
        elif (platform.system() == "Darwin"):
            transparent= 'systemTransparent'
            cardButton.preview.wm_attributes("-transparent", True)
            cardButton.preview.config(bg=transparent)
        cardButton.preview.canvas.config(bg=transparent)
        cardButton.preview.canvas.pack()
        return

    def hide_card(self, event, cardButton):
        cardButton.preview.canvas.pack_forget()
        cardButton.preview.destroy()
        return

    def show_deck_list(self):
        self.total = 0
        print("Du.decklist:" + str(du.decklist))
        while(du.decklist == {} or du.decklist == None):
            print("Waiting for decklist")
            du.getDecklist()
            print("Got:" + str(du.decklist))
        self.add_cards(sorted(du.decklist["CardsInDeck"], key = lambda card: du.decklist["CardsInDeck"][card]["Name"], reverse = True))
        for card in self.frameList:
            self.frameList[card].pack(side = "bottom")
        self.update_counters()

    def clear_recent(self):
        for card in self.cardList:
            self.cardList[card].recent = 0

def background_manager(results):
    time.sleep(1)
    print("Continuing background manager")
    last_results = results
    results = du.checkGameStat(results['lastGameID'], results['gameInfo'], results['ready'])
    print("Incoming results")
    print(results)
    if not (results['gameInfo'] == None):
        if(results['gameInfo']['GameState'] == None):
            print("No Game State")
            background_manager(results)
            return
    else:
        print("No gameInfo")
        background_manager(results)
        return
    print("Got through quick returns")
    if(results['gameInfo']['GameState'] == 'InProgress' and not last_results['gameInfo']['GameState'] == 'InProgress'):
        print("Starting app game")
        du.getDecklist()
        app.start_game()
    elif(results['gameInfo']['GameState'] == 'InProgress' and last_results['gameInfo']['GameState'] == 'InProgress'):
        cardsToRemove, cardsToAdd = du.checkBoardState()
        app.clear_recent()
        for card in cardsToRemove:
            if card[-2:] == 'T1':
                card = card[:-2]
            if card in app.cardList:
                app.decrement_card(app.cardList[card])
        for card in cardsToAdd:
            if card in app.cardList:
                app.increment_card(app.cardList[card])
            else:
                app.add_cards([card])
                app.frameList[card].pack(side = "bottom")
        app.update_counters()
        print("Checked board state")
    elif(not results['gameInfo']['GameState'] == 'InProgress' and (last_results['gameInfo'] == None or last_results['gameInfo']['GameState'] == 'InProgress')):
        if(last_results['gameInfo'] == None):
            print("Nothing in last_results")
            background_manager(results)
            return
        print("Ending app game")
        app.end_game()
        app.open_waiting_screen()
    background_manager(results)
    return



du.first_run()
parsedData = du.parseRiot()
dawg = du.dawg_generator(parsedData)

current_directory = os.getcwd()
final_directory = os.path.join(current_directory, r'alt_img')
if not os.path.exists(final_directory):
    os.makedirs(final_directory)

#threading.Timer(1.0, app.mainloop())

threads = list()
results = {'lastGameID': du.get_last_game_id(), 'gameInfo': {'GameState':None}, 'ready': False}
updateThread = threading.Thread(target=background_manager, args=(results,))
updateThread.daemon = True
threads.append(updateThread)
for thread in threads:
    thread.start()

root = Tk()
app = Application(master=root)
app.mainloop()



