from flask import Flask
from flask import render_template, jsonify, request, redirect, url_for, session
from flaskwebgui import FlaskUI
from werkzeug.utils import secure_filename
import sqlite3 as sql
import ebooklib
from ebooklib import epub
import base64
import os

con = sql.connect("ebooks.db")
cur = con.cursor()

def add_to_db(filepath):
    con = sql.connect("ebooks.db")
    cur = con.cursor()
    temp={}
    book = epub.read_epub(filepath)

    identifier = book.get_metadata('DC', 'identifier')[0][0]

    # Check if the book already exists in the database
    cur.execute("SELECT COUNT(*) FROM books WHERE identifier = ?", (identifier,))
    existing_record_count = cur.fetchone()[0]
    if existing_record_count > 0:
        print("Book with identifier '{}' already exists in the database.".format(identifier))
        con.close()
        return

    data = ['identifier', 'title', 'language', 'creator', 'contributor', 'publisher', 'rights', 'coverage', 'date', 'description']
    for meta in data:
        metadata = book.get_metadata('DC',meta)
        if metadata:
            temp[meta]=metadata[0][0]
        else:
            temp[meta]=None

    # Get the cover image item from the book

    if book.get_metadata('OPF','cover'):
        cover_item_id = book.get_metadata('OPF','cover')[0][1]['content']
        cover_item = book.get_item_with_id(cover_item_id)
        cover_image_data = cover_item.get_content()
        with open(os.path.join('static','images',f'{secure_filename(temp['identifier'])}.png'), 'wb') as file:
            file.write(cover_image_data)
        temp['image']=secure_filename(temp['identifier'])
    else:
        temp['image']=None
    temp['filepath']=filepath
    cur.execute("INSERT INTO books ('identifier', 'title', 'language', 'creator', 'contributor', 'publisher', 'rights', 'coverage', 'date', 'description','image','filepath') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(temp.values()))
    con.commit()
    con.close()
    

app = Flask(__name__)

import os

os.makedirs('ebooks', exist_ok=True)
UPLOAD_FOLDER = 'ebooks'
ALLOWED_EXTENSIONS = {'epub'}

app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'ILOVEBIGBLACKOILYGAYMEN'
app.config['SESSION_TYPE']= 'filesystem'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_html_from_epub_and_save(filepath):
    # Ensure the correct relative path to the "ebooks" folder
    
    # Read the EPUB file
    book = epub.read_epub(filepath)
    
    # Extract HTML content
    html_content = ''
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            html_content += item.get_content().decode('utf-8')
    
    return html_content


@app.route("/")
def index(): 
    con = sql.connect("ebooks.db")
    cur = con.cursor()

    try:
        # Execute a query to fetch all books from the database
        cur.execute("SELECT * FROM books")
        books = cur.fetchall()
    finally:
        # Close the cursor and database connection
        cur.close()
        con.close()

    return render_template("index.html", books=books)

@app.route("/add-file", methods=["GET","POST"])
def add_file():
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file", 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path=os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        add_to_db(file_path)
        return redirect(url_for("index"))
    
    return "File type not allowed", 400

@app.route('/details')
def book_details():
    book_id = request.args.get('id')
    session['book_id'] = book_id
    print(session.get('book_id'))
    # Find the book by ID
    con = sql.connect("ebooks.db")
    cur = con.cursor()
    book=cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book=book.fetchone()
    con.commit()
    con.close()
    if book is not None:
        return render_template('details.html', book=book)
    else:
        return jsonify("Book not found"), 404

@app.route('/book')
def book():
    con = sql.connect("ebooks.db")
    cur = con.cursor()
    id = session.get('book_id')
    file = cur.execute("SELECT filepath FROM books WHERE id=?", (id,))
    file=file.fetchone()[0]
    ebook_content=extract_html_from_epub_and_save(file)
    con.commit()
    con.close()
    return render_template('book.html', ebook_content=ebook_content)   

@app.route('/delete')
def delete():    
    con = sql.connect("ebooks.db")
    cur = con.cursor()
    id = session.get('book_id')
    file = cur.execute("SELECT filepath, image FROM books WHERE id=?", (id,))
    file=file.fetchone()
    filepath, image = file[0], (file[1]+'.png')
    image_path = os.path.join('static', 'images', image)
    os.remove(filepath)
    os.remove(image_path)
    cur.execute("DELETE FROM books WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("index"))


@app.route('/credits')
def credits():
    return render_template('credits.html')
    

if __name__ == "__main__":
  # If you are debugging you can do that in the browser:
  #app.run(host="0.0.0.0", port=5050)
  # If you want to view the flaskwebgui window:
  FlaskUI(app=app, server="flask", port=5050).run()



