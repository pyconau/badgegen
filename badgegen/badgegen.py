#!/usr/bin/env python
import datetime
import os
import pprint
import subprocess
import sys
import time
import argparse
import tomllib
import glob
import shutil

import attrs
import jinja2 as j2
import PIL.ImageFont
import requests
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H
import qrcode.image.svg



@attrs.define
class BadgeRuntime:
    config: dict = None
    badge_template: str = None
    top_half_light: str = None
    bottom_half_light: str = None
    top_half_tint: str = None
    bottom_half_tint: str = None
    pt_sans_bold: PIL.ImageFont.ImageFont = None
    pt_sans_bold_condensed: PIL.ImageFont.ImageFont = None
    pt_sans_regular: PIL.ImageFont.ImageFont = None
    pt_sans_regular_condensed: PIL.ImageFont.ImageFont = None
    template: j2.Template = None


def load_runtime(directory):
    print (f"Loading runtime from {directory}")
    if not os.path.exists(directory):
        print("No directory found")
        return BadgeRuntime()
        
    with open(f"{directory}/badgegen.toml", "rb") as f:
        CONFIG = tomllib.load(f)

    
    with(open(f"{directory}/assets/badge.svg")) as f:
        BADGE_TEMPLATE = f.read()
    
    with open(f"{directory}/assets/top-half-light.svg") as f:
        TOP_HALF_LIGHT = f.read()

    with open(f"{directory}/assets/bottom-half-light.svg") as f:
        BOTTOM_HALF_LIGHT = f.read()

    with open(f"{directory}/assets/top-half-tint.svg") as f:
        TOP_HALF_TINT = f.read()

    with open(f"{directory}/assets/bottom-half-tint.svg") as f:
        BOTTOM_HALF_TINT = f.read()
    
    # pt_sans_bold = PIL.ImageFont.truetype(f"{directory}/assets/PTS75F.ttf", size=100)
    # pt_sans_bold_condensed = PIL.ImageFont.truetype(f"{directory}/assets/PTN77F.ttf", size=100)
    # pt_sans_regular = PIL.ImageFont.truetype(f"{directory}/assets/PTS55F.ttf", size=100)
    # pt_sans_regular_condensed = PIL.ImageFont.truetype(f"{directory}/assets/PTN57F.ttf", size=100)

    pt_sans_bold = PIL.ImageFont.truetype(f"{os.environ['HOME']}/.fonts/PTS75F.ttf", size=100)
    pt_sans_bold_condensed = PIL.ImageFont.truetype(f"{os.environ['HOME']}/.fonts/PTN77F.ttf", size=100)
    pt_sans_regular = PIL.ImageFont.truetype(f"{os.environ['HOME']}/.fonts/PTS55F.ttf", size=100)
    pt_sans_regular_condensed = PIL.ImageFont.truetype(f"{os.environ['HOME']}/.fonts/PTN57F.ttf", size=100)

    return BadgeRuntime(
        config=CONFIG,
        badge_template=BADGE_TEMPLATE,
        top_half_light=TOP_HALF_LIGHT,
        bottom_half_light=BOTTOM_HALF_LIGHT,
        top_half_tint=TOP_HALF_TINT,
        bottom_half_tint=BOTTOM_HALF_TINT,
        pt_sans_bold=pt_sans_bold,
        pt_sans_bold_condensed=pt_sans_bold_condensed,
        pt_sans_regular=pt_sans_regular,
        pt_sans_regular_condensed=pt_sans_regular_condensed,
    )


LAST_UPDATE_FILE = '.last_update'



@attrs.define
class FontSettings:
    font: str
    ratio: float

def get_name_font_settings(name, font, condensed_font, max_width: float):
    width = font.getlength(name)
    if width < max_width:
        return FontSettings(font='normal', ratio=1)
    condensed_width = condensed_font.getlength(name)
    if condensed_width < max_width:
        return FontSettings(font='condensed', ratio=1)
    return FontSettings(font='condensed', ratio=max_width / condensed_width)


WIDTH_INSIDE_MARGINS_MM = 95
PRIMARY_NAME_SIZE = WIDTH_INSIDE_MARGINS_MM / 25 * 100
SECONDARY_NAME_SIZE = WIDTH_INSIDE_MARGINS_MM / 18 * 100
AFFILIATION_SIZE = WIDTH_INSIDE_MARGINS_MM / 8 * 100

@attrs.define
class BadgeParams:
    primary_name: str
    secondary_names: str
    affiliation: str
    order_code: str
    sort_number: str
    lozenge_text: str | None = None
    bg_color: str | None = None
    bg_ribbon_only: bool = False
    east_asian_name_order: bool = False
    psuedoanonymous_id: str | None = None

    @property
    def full_name(self):
        if self.east_asian_name_order:
            return f"{self.secondary_names} {self.primary_name}"
        else:
            return f"{self.primary_name} {self.secondary_names}"
    
    @property
    def text_color(self):
        if self.bg_color and not self.bg_ribbon_only:
            return "white"
        return "black"
    
    @property
    def qr_color(self):
        if self.bg_color and not self.bg_ribbon_only:
            return "white"
        return "black"

def generate_badge_svg(runtime, params: BadgeParams):
    #KXWDL-1
    primary_name_settings = get_name_font_settings(params.primary_name, runtime.pt_sans_bold, runtime.pt_sans_bold_condensed, PRIMARY_NAME_SIZE)
    secondary_name_settings = get_name_font_settings(params.secondary_names, runtime.pt_sans_regular, runtime.pt_sans_regular_condensed, SECONDARY_NAME_SIZE)
    affiliation_settings = get_name_font_settings(params.affiliation, runtime.pt_sans_regular, runtime.pt_sans_regular_condensed, AFFILIATION_SIZE)

    # factory = qrcode.image.svg.SvgImage
    qr_factory = qrcode.image.svg.SvgImage
    qr = qrcode.QRCode(image_factory=qr_factory, error_correction=ERROR_CORRECT_H)
    qr.add_data(params.psuedoanonymous_id)
    qr.make(fit=True)
    qr_image = qr.make_image(image_factory=qr_factory, attrib={"x": "-6", "y": "100"}, fill=params.qr_color)
    qr_svg = qr_image.to_string(encoding='unicode')
    
    print(params.primary_name or '<No Primary Name>', params.secondary_names or '<No Secondary Names>', params.psuedoanonymous_id)
 

    if params.lozenge_text:
        lozenge_text_width = runtime.pt_sans_bold.getlength(params.lozenge_text) * 7.5 / 100
    else:
        lozenge_text_width = None
    top_half = runtime.top_half_tint if params.bg_color and not params.bg_ribbon_only else runtime.top_half_light
    bottom_half = runtime.bottom_half_tint if params.bg_color else runtime.bottom_half_light
    
    return runtime.template.render(params=params, primary_name_settings=primary_name_settings, secondary_name_settings=secondary_name_settings, affiliation_settings=affiliation_settings, lozenge_text_width=lozenge_text_width, top_half=top_half, bottom_half=bottom_half, qr=qr_svg)

def generate_badge(runtime, params: BadgeParams):
    svg = generate_badge_svg(runtime, params)

    with open(f'output/svgs/{params.order_code}.svg', 'w') as f:
        f.write(svg)
    # Our SVG is 210 x 297 units
    # A4 == 8.27 x 11.69 inches
    # A4 == 210 x 297 mm
    # 2.54 cm = 1 inch
    # 25.4 mm = 1 inch <- This is our DPI factor

    subprocess.run(('svg2pdf', f'output/svgs/{params.order_code}.svg', f'output/pdfs/{params.order_code}.pdf', '--dpi', '25.4', '--text-to-paths'), check=True)


WATTLE_LEAF = '#00B159'
LORIKEET_BLUE = '#5B57A5'
LORIKEET_BLUE_MUTED = '#ADABD2'
RED_CENTRE = '#E01D43'


FRIDAY_ONLY = {
    569206,  # Friday Only 
    569207,  # Friday Only Student (EB?)
    569213,  # Tracks Only Enthusiast
    569214,  # Tracks Only Student
    569208,  # Tracks Only Speaker
}
SPRINTS_ONLY = 569209
SPRINTS_MONDAY = 569215 #unused
SPRINTS_TUESDAY = 569216 #unused

TEAM_MEMBERS = [
    569202
     637767 #Late Team Member
]

SPEAKERS = {
    569208,  # Tracks Only Speaker
    569203,  # Speaker
}
SPONSOR_GUEST = 569205

WORKSHOP_ONLY = 633942 #unused
WORKSHOP_1 = 633940 #unused
WORKSHOP_2 = 633939 #unused

TEE_TICKETS = {
    569212,  # T-Shirt Additional
    569211,  # T-Shirt Bundled
}

TICKET_ITEMS = {
    569195,  # Professional EB
    569196,  # Professional
    572936,  # Professional LB
    569197,  # Enthusiast EB
    569198,  # Enthusiast
    572937,  # Enthusiast LB
    569199,  # Student
    569199,  # Contributor
    629547,  # Exhibitor
    TEAM_MEMBER,  # Team Member
    SPONSOR_GUEST,  # Sponsor Guest
    *SPEAKERS,
    *FRIDAY_ONLY,
    SPRINTS_ONLY,  # Sprints Only
}

def paginate(url):
    PRETIX_TOKEN = os.environ['PRETIX_TOKEN']
    next_url = url
    while next_url:
        res = requests.get(
            next_url,
            headers={"Authorization": f"Token {PRETIX_TOKEN}"},
        )
        res.raise_for_status()
        data = res.json()
        next_url = data["next"]
        yield from data["results"]

def fetch(url):
    PRETIX_TOKEN = os.environ['PRETIX_TOKEN']
    res = requests.get(
        url,
        headers={"Authorization": f"Token {PRETIX_TOKEN}"},
    )
    res.raise_for_status()
    return res.json()


run_time = datetime.datetime.now(datetime.timezone.utc)
try:
    LAST_MODIFIED = datetime.datetime.fromtimestamp(os.path.getmtime(LAST_UPDATE_FILE), tz=datetime.timezone.utc)
except FileNotFoundError:
    LAST_MODIFIED = datetime.datetime(1970,1,1,0,0,0, tzinfo=datetime.timezone.utc)

def do_order(runtime, order):

    printables = [x for x in order['positions'] if x['item'] in TICKET_ITEMS]
    workshops = [x for x in order['positions'] if x['item'] in {WORKSHOP_1, WORKSHOP_2}]
    tees = [x for x in order['positions'] if x['item'] in {569200, 569201}]

    print (f'Order {order['code']} includes: \n\tTickets: {len(printables)} Workshops: {len(workshops)} Tees: {len(tees)}')
    

    for position in order['positions']:
        if position['item'] not in TICKET_ITEMS:
            print(f"Skipping {position['item']} - not a printable ticket type.")
            continue
        
        questions = {x['question_identifier']: x['answer'] for x in position['answers']}
        ticket_id = f"{position['order']}-{position['positionid']}"


        # sort out the annotations
        bg_color = None
        bg_ribbon_only = True
        lozenge_text = None
        generate_low_badge = False
        if questions.get('safety') == 'True':
            bg_ribbon_only = False
            bg_color = runtime.config['badge_design']['RED_CENTRE']
            lozenge_text = "SAFETY TEAM"
            generate_low_badge = True
        elif position['item'] in runtime.config['pretix_tickets']['TEAM_MEMBERS']:
            bg_ribbon_only = False
            generate_low_badge = True
            if questions['team'] == 'Core Team':
                bg_color = WATTLE_LEAF
                lozenge_text = "CORE TEAM"
            else:
                bg_color = LORIKEET_BLUE
                lozenge_text = questions['team'].upper()
                if lozenge_text == "VOLUNTEER TEAM":
                    lozenge_text = "VOLUNTEER"
        elif position['item'] in runtime.config['pretix_tickets']['SPEAKERS']:
            bg_color = WATTLE_LEAF
            lozenge_text = "SPEAKER"
        elif position['item'] == runtime.config['pretix_tickets']['SPONSOR_GUEST']:
            bg_color = LORIKEET_BLUE_MUTED
            lozenge_text = "SPONSOR GUEST"
        elif questions.get('sponsor') == "True":
            bg_color = LORIKEET_BLUE
            lozenge_text = "SPONSOR"
        elif position['item'] in runtime.config['pretix_tickets']['SPONSORS']:
            bg_color = LORIKEET_BLUE
            lozenge_text = "SPONSOR"
        elif position['item'] in runtime.config['pretix_tickets']['FRIDAY_ONLY']:
            lozenge_text = "FRIDAY ONLY"
        params = BadgeParams(
            primary_name=questions.get('primary_name', ''),
            secondary_names=questions.get('additional_names', ''),
            east_asian_name_order=questions.get('east_asian_name_order', 'False') == 'True',
            affiliation=questions.get('affiliation', ''),
            order_code=ticket_id,
            sort_number=questions.get('sort_number'),
            bg_color=bg_color,
            lozenge_text=lozenge_text,
            bg_ribbon_only=bg_ribbon_only,
            psuedoanonymous_id=position['pseudonymization_id'],
        )
        generate_badge(runtime, params)
        if generate_low_badge:
            generate_badge(runtime, BadgeParams(
                primary_name=params.primary_name,
                secondary_names=params.secondary_names,
                east_asian_name_order=params.east_asian_name_order,
                affiliation=params.affiliation,
                order_code=params.order_code + 'L',
                sort_number=params.sort_number,
                psuedoanonymous_id=position['pseudonymization_id'],
            ))

def do_all_badges(runtime):
    for order in paginate('https://pretix.eu/api/v1/organizers/pyconau/events/2024/orders/'):
        if datetime.datetime.fromisoformat(order['payments'][0]['created']) < LAST_MODIFIED:
            continue
        do_order(runtime, order)

def install_fonts(directory):
    # Install fonts from the directory
    fonts = glob.glob(f"{directory}/assets/*.ttf")
    # ['2024/assets/PTS55F.ttf', '2024/assets/PTS75F.ttf', '2024/assets/PTN77F.ttf', '2024/assets/PTN57F.ttf']
    
    # These destinations much match where svg2pdf looks for fonts
    # Specifically, see https://github.com/RazrFalcon/fontdb/blob/master/src/lib.rs#L400
    destinations = {
        # 'Linux': f"{os.environ['HOME']}/.fonts/",
        'Linux': f"{os.environ['HOME']}/.local/share/fonts",
        'Windows': f"{os.environ['HOME']}AppData\\Local\\Microsoft\\Windows\\Fonts",
        'Darwin': f"{os.environ['HOME']}/Library/Fonts/",
    }
    destination_dir = destinations[os.uname().sysname]
    os.makedirs(destination_dir, exist_ok=True)
    
    for font in fonts:
        filename = os.path.basename(font)
        shutil.copy(font, destination_dir)


def do_experimental(runtime):
    admissions = []
    # get all orders
    for order in paginate('https://pretix.eu/api/v1/organizers/pyconau/events/2024/orders/'):
        # "answers": [
        #     {
        #         "question": 140758,
        #         "answer": "Jack",
        #         "question_identifier": "primary_name",
        #         "options": [],
        #         "option_identifiers": []
        #     },
        #     {
        #         "question": 140759,
        #         "answer": "Skinner",
        #         "question_identifier": "additional_names",
        #         "options": [],
        #         "option_identifiers": []
        #     },
        
        for position in order['positions']:

            # is admission by config'd ID's? e.g. "569203"
            # => Is a new admission ticket
            # => Generate a fuzzy ID
            # is addon to existing admission?
            # => Attach to that badge as an entitlement based on product ID
            # can fuzzy id match?
            # Spit out edge case?

            
            fuzzy = {}
            for answers in position['answers']:
                if answers['question'] in [140758, 140759]:
                    names[answers['question']] = answers['answer']
            print(names)
        
        # names = [answer in order['answers'] if answer['question'] in [140758, 140759] else '']
        print(names)
        admission_key = f"{order['email']}"
        break


    
    print(len(orders))
            


parser = argparse.ArgumentParser(description="Generate badges for PyCon AU.")
parser.add_argument('-a', '--all', help="generate all badges", default=False, action='store_true')
parser.add_argument('-o', '--order', type=str, help="generate badges for a given order", default=None, action='store')
parser.add_argument('-d', '--directory', type=str, help="directory for assets. Defaults current year", default=None, action='store')
parser.add_argument('-x', '--experimental', help="Experimental behaviour", default=False, action='store_true')

if __name__ == "__main__":
    args = parser.parse_args()
    directory = args.directory or str(datetime.datetime.now(datetime.timezone.utc).year)
    
    install_fonts(directory)

    runtime = load_runtime(directory)

    if args.experimental:
        print("Experimental behaviour")
        do_experimental(runtime)

    runtime.template = j2.Environment(
        loader=j2.DictLoader({'badge.svg.j2': runtime.badge_template}),
        autoescape=True,
    ).get_template('badge.svg.j2')

    os.makedirs('output/svgs', exist_ok=True)
    os.makedirs('output/pdfs', exist_ok=True)
    
    if 'PRETIX_TOKEN' not in os.environ:
        print("Please set the PRETIX_TOKEN environment variable.")
        sys.exit(1)

    if args.all:
        print("Generating all badges")
        do_all_badges(runtime)
    elif args.order:
        print("Action: Badges for order", args.order)
        
        order = fetch(f'https://pretix.eu/api/v1/organizers/pyconau/events/2024/orders/{args.order}/')
        do_order(runtime, order)
    
    else:
        parser.print_help()
        sys.exit(1)



# if __name__ == "__main__":
#     """
#     generate_badge_svg(BadgeParams(
#        # primary_name="🌈🤦‍♀️🎮👻",
#        # secondary_names="יעקב",
#        primary_name="John",
#        secondary_names="Jacob Jingleheimer Schmidt",
#        affiliation="ACME Widgets Corp",
#        order_code="ABCDE-1",
#        sort_number="24",
#        lozenge_text="AV VOLUNTEER",
#        bg_color="#00B159",
#        bg_ribbon_only=True,
#     ))
#     """
#     do_all_badges()
#     Path(LAST_UPDATE_FILE).touch()
