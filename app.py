from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
import sqlite3
from datetime import datetime
import os
from gtts import gTTS
import pygame
import io
import tempfile
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import ImageReader
import qrcode

app = Flask(__name__)

# Database configuration
DATABASE = 'database.db'

def init_db():
    """Initialize the SQLite database with tickets table"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create tickets table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'waiting',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection with row factory for easier data access"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

def generate_next_ticket_number():
    """
    Generate a new ticket number by finding the last ticket number in DB
    and incrementing it (e.g., H001 -> H002)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the last ticket number from database
    cursor.execute('SELECT ticket_number FROM tickets ORDER BY id DESC LIMIT 1')
    last_ticket = cursor.fetchone()
    
    if last_ticket:
        # Extract number from ticket (e.g., "H001" -> 1)
        last_number = int(last_ticket['ticket_number'][1:])
        new_number = last_number + 1
    else:
        # First ticket
        new_number = 1
    
    # Format as H001, H002, etc.
    new_ticket_number = f"H{new_number:03d}"
    conn.close()
    
    return new_ticket_number

def play_announcement(ticket_number, room="Room 1"):
    """
    Play text-to-speech announcement for called ticket
    Uses gTTS (Google Text-to-Speech) and pygame for audio playback
    """
    try:
        # Create announcement text
        announcement_text = f"Ticket {ticket_number}, please proceed to {room}"
        
        # Generate speech using gTTS
        tts = gTTS(text=announcement_text, lang='en')
        
        # Create a temporary file that won't be deleted immediately
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_filename = os.path.join(temp_dir, f"announcement_{ticket_number}_{int(datetime.now().timestamp())}.mp3")
        
        # Save TTS to file
        tts.save(temp_filename)
        
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Load and play audio
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        # Wait for playback to complete
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Clean up temporary file after playback
        try:
            os.unlink(temp_filename)
        except:
            pass  # Ignore cleanup errors
            
        print(f"Announcement played: {announcement_text}")
            
    except Exception as e:
        print(f"Error playing announcement: {e}")
        # Fallback: just print the announcement
        print(f"ANNOUNCEMENT: Ticket {ticket_number}, please proceed to {room}")

@app.route('/')
def index():
    """Redirect home page to ticket issuing page"""
    return redirect(url_for('get_ticket'))

@app.route('/get_ticket')
def get_ticket():
    """
    Ticket Issuing Page (for patients)
    Displays a button that says "Get Ticket"
    """
    return render_template('get_ticket.html')

@app.route('/issue_ticket', methods=['POST'])
def issue_ticket():
    """
    Handle ticket issuance when patient clicks "Get Ticket" button
    Generates new ticket number and saves to database
    """
    try:
        # Generate new ticket number
        ticket_number = generate_next_ticket_number()
        
        # Save ticket to database with "waiting" status
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tickets (ticket_number, status, timestamp)
            VALUES (?, ?, datetime('now'))
        ''', (ticket_number, 'waiting'))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'ticket_number': ticket_number,
            'message': f'Your ticket number is {ticket_number}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error issuing ticket: {str(e)}'
        })

@app.route('/display')
def display():
    """
    Display Screen (waiting room monitor)
    Shows current ticket being served and next 3 waiting tickets
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current ticket being served
    cursor.execute('''
        SELECT ticket_number FROM tickets 
        WHERE status = 'serving' 
        ORDER BY timestamp ASC 
        LIMIT 1
    ''')
    current_ticket = cursor.fetchone()
    
    # Get next 3 waiting tickets
    cursor.execute('''
        SELECT ticket_number FROM tickets 
        WHERE status = 'waiting' 
        ORDER BY timestamp ASC 
        LIMIT 3
    ''')
    waiting_tickets = cursor.fetchall()
    
    conn.close()
    
    return render_template('display.html', 
                         current_ticket=current_ticket,
                         waiting_tickets=waiting_tickets)

@app.route('/staff')
def staff():
    """
    Staff Panel (for reception/doctors)
    Shows list of waiting tickets and controls for managing queue
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all waiting tickets
    cursor.execute('''
        SELECT id, ticket_number, timestamp FROM tickets 
        WHERE status = 'waiting' 
        ORDER BY timestamp ASC
    ''')
    waiting_tickets = cursor.fetchall()
    
    # Get currently serving ticket
    cursor.execute('''
        SELECT ticket_number FROM tickets 
        WHERE status = 'serving' 
        ORDER BY timestamp ASC 
        LIMIT 1
    ''')
    current_serving = cursor.fetchone()
    
    conn.close()
    
    return render_template('staff.html', 
                         waiting_tickets=waiting_tickets,
                         current_serving=current_serving)

@app.route('/call_next', methods=['POST'])
def call_next():
    """
    Call next ticket in queue
    Updates database status from 'waiting' to 'serving'
    Plays text-to-speech announcement
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mark any currently serving ticket as done
        cursor.execute('''
            UPDATE tickets SET status = 'done' 
            WHERE status = 'serving'
        ''')
        
        # Get the next waiting ticket
        cursor.execute('''
            SELECT id, ticket_number FROM tickets 
            WHERE status = 'waiting' 
            ORDER BY timestamp ASC 
            LIMIT 1
        ''')
        next_ticket = cursor.fetchone()
        
        if next_ticket:
            # Update ticket status to serving
            cursor.execute('''
                UPDATE tickets SET status = 'serving' 
                WHERE id = ?
            ''', (next_ticket['id'],))
            
            conn.commit()
            conn.close()
            
            # Play announcement for called ticket
            play_announcement(next_ticket['ticket_number'])
            
            return jsonify({
                'success': True,
                'ticket_number': next_ticket['ticket_number'],
                'message': f'Called ticket {next_ticket["ticket_number"]}'
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'No waiting tickets available'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error calling next ticket: {str(e)}'
        })

@app.route('/complete_current', methods=['POST'])
def complete_current():
    """
    Mark currently serving ticket as completed
    Allows staff to finish with current patient before calling next
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mark currently serving ticket as done
        cursor.execute('''
            UPDATE tickets SET status = 'done' 
            WHERE status = 'serving'
        ''')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Current ticket marked as completed'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error completing ticket: {str(e)}'
        })

@app.route('/print_ticket/<ticket_number>')
def print_ticket(ticket_number):
    """
    Generate a PDF ticket for printing
    Creates a professional-looking ticket with QR code
    """
    try:
        # Use the simple canvas approach for better QR code control
        buffer = io.BytesIO()
        
        # Create canvas (4x6 inch ticket)
        width, height = 4*72, 6*72  # Convert inches to points
        p = canvas.Canvas(buffer, pagesize=(width, height))
        
        # Hospital Header
        p.setFont("Helvetica-Bold", 18)
        p.setFillColor(colors.blue)
        p.drawCentredString(width/2, height-40, "🏥 HOSPITAL QUEUE")
        
        # Ticket Number (Large and Bold)
        p.setFont("Helvetica-Bold", 36)
        p.setFillColor(colors.red)
        p.drawCentredString(width/2, height-100, ticket_number)
        
        # Generate and embed QR Code
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=6,
                border=2,
            )
            qr.add_data(f"Hospital-Ticket:{ticket_number}")
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR image to temporary buffer
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Calculate QR code position (center of ticket)
            qr_size = 100  # 100 points = ~1.4 inches
            qr_x = (width - qr_size) / 2
            qr_y = height - 220  # Position below ticket number
            
            # Draw QR code on PDF
            p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)
            
            # Close QR buffer
            qr_buffer.close()
            
            print(f"QR code generated successfully for ticket {ticket_number}")
            
        except Exception as qr_error:
            print(f"QR code generation failed: {qr_error}")
            # Draw a placeholder rectangle where QR code should be
            qr_size = 100
            qr_x = (width - qr_size) / 2
            qr_y = height - 220
            p.setStrokeColor(colors.grey)
            p.setFillColor(colors.lightgrey)
            p.rect(qr_x, qr_y, qr_size, qr_size, fill=1)
            p.setFillColor(colors.black)
            p.setFont("Helvetica", 10)
            p.drawCentredString(width/2, qr_y + qr_size/2, "QR Code")
        
        # Instructions below QR code
        p.setFont("Helvetica", 12)
        p.setFillColor(colors.black)
        p.drawCentredString(width/2, height-250, "Please wait for your number to be called")
        
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, height-270, "Show this ticket at reception")
        
        # Timestamp at bottom
        p.setFont("Helvetica", 9)
        p.setFillColor(colors.grey)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        p.drawCentredString(width/2, 30, f"Issued: {now}")
        
        # Draw border around entire ticket
        p.setStrokeColor(colors.blue)
        p.setLineWidth(2)
        p.rect(5, 5, width-10, height-10, fill=0)
        
        # Save PDF
        p.save()
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=ticket_{ticket_number}.pdf'
        
        return response
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error generating PDF: {str(e)}'
        })

@app.route('/test_qr/<ticket_number>')
def test_qr(ticket_number):
    """
    Test endpoint to generate just a QR code image
    Visit /test_qr/H001 to see if QR generation works
    """
    try:
        import base64
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"Hospital-Ticket:{ticket_number}")
        qr.make(fit=True)
        
        # Create image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for display in browser
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Return as image
        from flask import Response
        return Response(buffer.getvalue(), mimetype='image/png')
        
    except Exception as e:
        return f"QR generation error: {e}"

@app.route('/simple_print/<ticket_number>')
def simple_print_ticket(ticket_number):
    """
    Simple PDF ticket generator (fallback if reportlab fails)
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=(4*72, 6*72))  # 4x6 inches in points
        
        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(2*72, 5.2*72, "🏥 HOSPITAL QUEUE")
        
        # Ticket Number
        p.setFont("Helvetica-Bold", 28)
        p.setFillColor(colors.red)
        p.drawCentredString(2*72, 4.2*72, ticket_number)
        
        # Generate simple QR code and add to canvas
        try:
            qr = qrcode.QRCode(version=1, box_size=2, border=1)
            qr.add_data(f"Hospital Ticket: {ticket_number}")
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Draw QR code on canvas
            p.drawImage(ImageReader(qr_buffer), 1.2*72, 2.5*72, width=1.6*72, height=1.6*72)
            qr_buffer.close()
            
        except Exception as qr_error:
            print(f"QR code error in simple PDF: {qr_error}")
        
        # Instructions
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.black)
        p.drawCentredString(2*72, 2.2*72, "Please wait for your number")
        p.drawCentredString(2*72, 2.0*72, "to be called")
        
        # Timestamp
        p.setFont("Helvetica", 8)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        p.drawCentredString(2*72, 1.2*72, f"Issued: {now}")
        
        p.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=ticket_{ticket_number}.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating PDF: {str(e)}'
        })
def display_data():
    """
    API endpoint for display screen to get updated data
    Used by JavaScript for automatic refresh
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current serving ticket
    cursor.execute('''
        SELECT ticket_number FROM tickets 
        WHERE status = 'serving' 
        ORDER BY timestamp ASC 
        LIMIT 1
    ''')
    current_ticket = cursor.fetchone()
    
    # Get next 3 waiting tickets
    cursor.execute('''
        SELECT ticket_number FROM tickets 
        WHERE status = 'waiting' 
        ORDER BY timestamp ASC 
        LIMIT 3
    ''')
    waiting_tickets = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'current_ticket': current_ticket['ticket_number'] if current_ticket else None,
        'waiting_tickets': [ticket['ticket_number'] for ticket in waiting_tickets]
    })

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    
    # Run Flask app in debug mode
    app.run(debug=True, host='0.0.0.0', port=5000)