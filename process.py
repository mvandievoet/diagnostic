from flask import Flask, render_template, request, redirect, session
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections.polar import PolarAxes
from matplotlib.projections import register_projection
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D
import pandas as pd
import imgkit
from fpdf import FPDF
from datetime import datetime
import imageio
from email.message import EmailMessage
import imghdr
import smtplib
import os
import time

WIDTH = 210
HEIGHT = 297
DATE = "dd/mm/yy"
COMPANY_NAME = ""
COMPANY_NAME_NO_SCPACE = ""
DOSSIER_NUM = 0
NOM = ""
EMAIL = ""
EMAIL_ADDRESS = os.environ.get('EMAIL_USR')
EMAIL_PSW = os.environ.get('EMAIL_PSW')
EMAIL_NUM = 0


app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process():
    result = request.form["param1"]
    fields = request.form["param2"]

    result = toPrettyArray(result)
    fields = toPrettyArray(fields)

    if(result[0] == "Accélérer le développement de votre entreprise"):
        thread1 = threading.Thread(target=compute_dev, args=(result, fields))
        thread1.start()
    else:
        thread2 = threading.Thread(target=compute_ven, args=(result, fields))
        thread2.start()
    
    return "hey"


def toPrettyArray(result):
    result = result.split("\",\"")
    result[0] = result[0].replace("\"",'')
    result[-1] = result[-1].replace("\"",'')
    return result
    
# function for the "developpement" part
def compute_dev(result, fields):
    del result[59:88]
    result_numbers = result[1:-3]
    del result[1:-3]

    set_global_vars(result)

    for i in range(len(result_numbers)):
        result_numbers[i] = int(result_numbers[i])

    facteurs = ['Sens','Etat d\'esprit', 'Vision', 'Business Model', 'Stratégie et roadmap', 'Connecter les équipes', 'Alliances stratégiques', 'Ventes online / offline']
    av_results = [average(result_numbers, 0, 5), average(result_numbers, 6, 11), average(result_numbers, 12, 16), average(result_numbers, 17, 24),
    average(result_numbers, 25, 31), average(result_numbers, 32, 39), average(result_numbers, 40, 44), average(result_numbers, 45, 57)]
    df = pd.DataFrame(columns = ['8 facteurs clés', 'Score sur 10'])
    df['8 facteurs clés'] = facteurs
    df['Score sur 10'] = av_results

    questions = fields[1:59]

    draw_score_table(df)
    draw_radar_chart_dev(result[-1], df)
    draw_question_answer(questions, result_numbers, 'dev')
    make_pdf('dev')
    send_email()


# function for the "ventes online" part
def compute_ven(result, fields):
    result_numbers = result[59:88]
    del result[1:-3]
    set_global_vars(result)

    for i in range(len(result_numbers)):
        result_numbers[i] = int(result_numbers[i])
    
    facteurs = ['Proposition de valeur unique','Cible / Persona', 'Environnement / Concurrence', 'Canaux', 'Référencement et audiences',
     'Contenu', 'Funnel', 'Goals & Metrics']
    av_results = [average(result_numbers, 0, 2), average(result_numbers, 3, 5), average(result_numbers, 6, 8), average(result_numbers, 9, 12),
    average(result_numbers, 13, 16), average(result_numbers, 17, 20), average(result_numbers, 21, 24), average(result_numbers, 25, 28)]
    df = pd.DataFrame(columns = ['8 facteurs clés', 'Score sur 10'])
    df['8 facteurs clés'] = facteurs
    df['Score sur 10'] = av_results

    questions = fields[59:88]

    draw_score_table(df)
    draw_radar_chart_ven(result[-1], df)
    draw_question_answer(questions, result_numbers, 'ventes')
    make_pdf('ventes')
    send_email()


def set_global_vars(result):
    global COMPANY_NAME
    global NOM
    global EMAIL
    COMPANY_NAME = result[-1]
    NOM = result[-2]
    EMAIL = result[-3]


def average(arr, start, finish):
    sum = 0
    for i in range(start, finish+1):
        sum = arr[i] + sum

    avr = sum / (finish + 1 - start)
    return avr


def color_back(val):
    if(type(val) == str):
        color = ""
    elif val >= 8:
        color = '#e6ffe6'
    elif val < 5:
        color = '#ffe6e6'
    else:
        color = '#FFDDAF'
    return 'background-color: %s' % color


def draw_score_table(df):
    df_styled = df.style.applymap(color_back).format({'Score sur 10': '{:,.2f}'.format}).hide_index().set_table_styles([
        {"selector": "th", "props": [("text-align", "center"), ('font-size', '13pt'), ('font-style', 'Calibri')]},
        {'selector': 'td', 'props': [('font-size', '11pt'), ('font-style', 'Calibri'), ('line-height', '200%')]}])\
        .set_properties(subset=["Score sur 10"], **{'text-align': 'center'})\
        .set_properties(subset=["8 facteurs clés"], **{'border-bottom':'solid', 'text-align': 'left', 'border-width' : '0.5px', 'column-width': '250px'})

    imgkit.from_string(df_styled.render(), f'resources/score_tables/im{DOSSIER_NUM}.png')


def radar_factory(num_vars, frame='circle'):
    """Create a radar chart with `num_vars` axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle' | 'polygon'}
        Shape of frame surrounding axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)

    class RadarAxes(PolarAxes):

        name = 'radar'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location('N')

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            # FIXME: markers at x[0], y[0] get doubled-up
            if x[0] != x[-1]:
                x = np.concatenate((x, [x[0]]))
                y = np.concatenate((y, [y[0]]))
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            # The Axes patch must be centered at (0.5, 0.5) and of radius 0.5
            # in axes coordinates.
            if frame == 'circle':
                return Circle((0.5, 0.5), 0.5)
            elif frame == 'polygon':
                return RegularPolygon((0.5, 0.5), num_vars,
                                      radius=.5, edgecolor="k")
            else:
                raise ValueError("unknown value for 'frame': %s" % frame)

        def draw(self, renderer):
            """ Draw. If frame is polygon, make gridlines polygon-shaped """
            if frame == 'polygon':
                gridlines = self.yaxis.get_gridlines()
                for gl in gridlines:
                    gl.get_path()._interpolation_steps = num_vars
            super().draw(renderer)


        def _gen_axes_spines(self):
            if frame == 'circle':
                return super()._gen_axes_spines()
            elif frame == 'polygon':
                # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
                spine = Spine(axes=self,
                              spine_type='circle',
                              path=Path.unit_regular_polygon(num_vars))
                # unit_regular_polygon gives a polygon of radius 1 centered at
                # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
                # 0.5) in axes coordinates.
                spine.set_transform(Affine2D().scale(.5).translate(.5, .5)
                                    + self.transAxes)


                return {'polar': spine}
            else:
                raise ValueError("unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta


def draw_radar_chart_dev(company_name, df):
    
    data = [['Sens\n','Ventes online /            \n offline             ', 'Alliances                \n stratégiques                  ' , 
         'Connecter                \nles équipes                ', '\nStratégie\net roadmap', 
         '              Business\n               Model', '       Vision', '            Etat\n            d\'esprit'],
            ('', [
                df['Score sur 10'],
            [0,0,0,0,0,0,0,0]])]

    N = len(data[0])
    theta = radar_factory(N, frame='polygon')

    spoke_labels = data.pop(0)
    title, case_data = data[0]

    plt.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
    fig.subplots_adjust(top=0.85, bottom=0.05)

    ax.set_rgrids([2, 4, 6, 8, 10])
    ax.set_title(title,  position=(0.5, 1.1), ha='center')

    for d in case_data:
        line = ax.plot(theta, d)
        ax.fill(theta, d,  alpha=0.25)
    ax.set_varlabels(spoke_labels)

    plt.xlim(0, 12)
    plt.ylim(0, 10)

    plt.savefig(f"resources/radar_charts/im{DOSSIER_NUM}.png")
    

def draw_radar_chart_ven(company_name, df):
    
    data = [['Proposition de\nvaleur unique\n\n', 'Goals &          \n Metrics           ', 'Funnel         ', 'Contenu           ',
         '\nRéférencement\n et audiences', '           Canaux', 
         '                      Environnement /\n                    Concurrence', '             Cible /\n             Persona'],
            ('', [
                df['Score sur 10'],
            [0,0,0,0,0,0,0,0]])]

    N = len(data[0])
    theta = radar_factory(N, frame='polygon')

    spoke_labels = data.pop(0)
    title, case_data = data[0]

    plt.rcParams.update({'font.size': 16})

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
    fig.subplots_adjust(top=0.85, bottom=0.05)

    ax.set_rgrids([2, 4, 6, 8, 10])
    ax.set_title(title,  position=(0.5, 1.1), ha='center')

    for d in case_data:
        line = ax.plot(theta, d)
        ax.fill(theta, d,  alpha=0.25)
    ax.set_varlabels(spoke_labels)

    plt.xlim(0, 12)
    plt.ylim(0, 10)

    plt.savefig(f"resources/radar_charts/im{DOSSIER_NUM}.png")
    

def draw_question_answer(questions, answers, s):
    category = []
    if s == 'ventes':
        category = ["Proposition de valeur unique"] * 3
        category.extend(["Cible / Persona"] * 3 + ["Environnement / Concurrence"] * 3 + ["Canaux"] * 4)
        category.extend(["Référencement et audiences"] * 4 + ["Contenu"] * 4 + ["Funnel"] * 4 + ["Goals & Metrics"] * 4)
    else:
        category = ["Sens"] * 6
        category.extend(["Etat d'esprit"] * 6 + ["Vision"] * 5 + ["Business Model"] * 8)
        category.extend(["Stratégie et roadmap"] * 7 + ["Connecter les équipes"] * 8 + ["Alliances stratégiques"] * 5 + ["Ventes online / offline"] * 13)

    df = pd.DataFrame(columns = ['Affirmation', 'Score sur 10', 'Facteur clé'])
    df['Affirmation'] = questions
    df['Score sur 10'] = answers
    df['Facteur clé'] = category

    df_styled = df.style.format({'Score sur 10': '{:,.2f}'.format}).hide_index()\
        .set_properties(subset=["Score sur 10"], **{'text-align': 'center', 'column-width': '300px'})\
        .set_properties(subset=["Facteur clé"], **{'text-align': 'center', 'column-width': '400px'})\
        .set_properties(subset=["Affirmation"], **{'text-align': 'left'}).set_table_styles([
        {"selector": "th", "props": [("text-align", "center"), ('font-size', '13pt'), ('font-style', 'Calibri')]},
        {'selector': 'td', 'props': [('font-size', '12pt'), ('font-style', 'Calibri'), ('line-height', '150%'), ('border-bottom','solid'), ('border-width', '0.5px')]}])

    imgkit.from_string(df_styled.render(), f'resources/question_answer/im{DOSSIER_NUM}.png')

    img = imageio.imread(f'resources/question_answer/im{DOSSIER_NUM}.png')
    height, width, x = img.shape

    # Cut the image
    if s == "ventes":
        height_cutoff = height // 2 + 105
        s1 = img[:height_cutoff, :]
        s2 = img[height_cutoff:, :]
    else:
        height_cutoff1 = 930
        height_cutoff2 = 2370
        s1 = img[:height_cutoff1, :]
        s2 = img[height_cutoff1:height_cutoff2, :]
        s3 = img[height_cutoff2:, :]
        imageio.imwrite(f'resources/question_answer/im{DOSSIER_NUM}_3.png', s3)

    imageio.imwrite(f'resources/question_answer/im{DOSSIER_NUM}_1.png', s1)
    imageio.imwrite(f'resources/question_answer/im{DOSSIER_NUM}_2.png', s2)


def make_pdf(s):
    print("/nI am making the pdf/n")
    global DATE
    global DOSSIER_NUM
    global COMPANY_NAME_NO_SCPACE

    DATE = (datetime.today()).strftime('%d/%m/%y')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)

    # add letterhead
    pdf.image('resources/letterhead.png', 0, 0, WIDTH)

    # add title and date
    pdf.ln(60)
    pdf.set_font('Helvetica', 'BU', 24)

    if s == "ventes":
        pdf.write(10, f'Diagnostic {COMPANY_NAME} : booster vos ventes en ligne')
    else:
        pdf.write(10, f'Diagnostic {COMPANY_NAME} : accélérer vos projets')
    pdf.ln(10)
    pdf.set_font('Helvetica', '',  16)
    pdf.write(10, f'{DATE}')

    # add 8 facteurs cles
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B',  16)
    pdf.write(20, '1. Les 8 facteurs clés de OuiTransform')
    pdf.ln(5)
    pdf.image('resources/8ventes.png', 15, 125, WIDTH-40)


    # add score card
    pdf.add_page()
    pdf.ln(15)
    #pdf.set_font('Helvetica', 'B',  16)
    pdf.write(20, '2. Vos scores')
    pdf.image(f'resources/score_tables/im{DOSSIER_NUM}.png', 20, 42, WIDTH-5)

    # add radar chart
    pdf.image(f'resources/radar_charts/im{DOSSIER_NUM}.png', 15, 113, WIDTH-40)
    pdf.ln(85)
    pdf.write(20, '3. Visualiser les facteurs à améliorer')
    

    # add free call text
    pdf.add_page()
    pdf.ln(15)
    pdf.write(20, '4. 30 minutes pour échanger')
    pdf.ln(20)
    pdf.set_font('Helvetica', '',  11)
    pdf.write(5, 'OuiTransform vous offre 30 minutes avec notre équipe pour échanger sur vos résultats, identifiez les leviers de croissance pour booster votre e-commerce.\n\nRéservez votre appel maintenant ici : https://ouitransform.com/contact/\n\nVisitez notre site pour en savoir plus sur notre approche : https://www.ouitransform.com/developper-vos-ventes-en-ligne')

    # add full responses
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B',  16)
    pdf.write(20, '5. Vos réponses')
    pdf.image(f'resources/question_answer/im{DOSSIER_NUM}_1.png', 10, 110, WIDTH-20)

    pdf.add_page()
    pdf.image(f'resources/question_answer/im{DOSSIER_NUM}_2.png', 10, 15, WIDTH-20)

    if s != 'ventes':
        pdf.add_page()
        pdf.image('tests/face3.png', 10, 15, WIDTH-20)

    COMPANY_NAME_NO_SCPACE = COMPANY_NAME.replace(" ", "_")
    pdf.output(f'resources/report/report_{COMPANY_NAME_NO_SCPACE}.pdf', 'F')
    DOSSIER_NUM = DOSSIER_NUM + 1


def send_email():
    global EMAIL_NUM
    msg = EmailMessage()
    msg['Subject'] = "Diagnostic OuiTransform"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL
    msg.set_content(f'Bonjour {NOM},\n\n Merci d’avoir participé à notre diagnostic en ligne.\n\nVous retrouvez en pièce jointe vos résultats pour identifier et mettre en évidence les challenges prioritaires pour accélérer votre développement et transformer votre entreprise.\n\nOuiTransform vous offre 30 minutes pour échanger sur vos résultats et discuter des opportunités pour faire grandir votre business. Vous pouvez réserver un appel en répondant à cet email ou via notre site : https://ouitransform.com/contact/\n\nAu plaisir d’en discuter avec vous.\n\nL’équipe OuiTransform')

    time.sleep(3)

    with open(f'resources/report/report_{COMPANY_NAME_NO_SCPACE}.pdf', 'rb') as f:
            file_data = f.read()
            file_name = f.name
    
    msg.add_attachment(file_data, maintype='image', subtype='octet-stream', filename=os.path.basename(file_name))


    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PSW)
        smtp.send_message(msg)
        print(f"Email number {EMAIL_NUM} was just sent out !")
        EMAIL_NUM = EMAIL_NUM + 1


if __name__ == '__main__':
    app.run(debug='true')