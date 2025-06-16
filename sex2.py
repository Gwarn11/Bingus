import socket
import threading
import json
import time
import random
import re
import os
import hashlib
import secrets
from collections import deque
from enum import Enum
import queue

# --- Server Configuration ---
HOST = '127.0.0.1'
PORT = 65432
MAX_CONNECTIONS = 20
SAVE_DIR = "save_files"
CONFIG_FILE = "config.json"

class C: # Color Class
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'

# --- Admin & GM Configuration ---
ADMIN_PIN = "6678"
ADMIN_USERS = ["Admin"]
GM_ACCOUNTS = 
{"DungeonMaster": "p@ssword123"}

# --- Helper Enums ---
class GameState(Enum):
    LOBBY = "LOBBY"
    CHARACTER_CREATION = "CHARACTER_CREATION"
    EXPLORATION = "EXPLORATION"
    COMBAT = "COMBAT"

# --- Static Game Data ---
HIT_LOCATIONS = {1: "Head", 2: "Torso", 3: "Left Arm", 4: "Right Arm", 5: "Left Leg", 6: "Right Leg"}

SKILLS = ["Asskissing", "Astral Navigation", "Awareness", "Axe", "Bash", "Charm", "Check Humors", "Climbing", "Cooking", "Corruption", "Cyber Karate", "Dance", "Dig", "Disguise", "Explosives", "Fashion", "Fencing", "Finance", "Gaming", "Gambling", "Hacking", "Heavy Weapon", "Intimidation", "Knife", "Levitation", "Medicine", "Meditation", "Pilot", "Pistol", "Public Speaking", "Rage", "Rifle", "Running", "Shotgun", "Skulk", "Sniper Rifle", "Spear", "Tech", "Track", "Traps", 
"Worship The Consumer", "Worship The Invisible Hand", "Worship The Pig God", "Zero-G Combat", "Pilot Gaming Throne", "Pilot Exomech", "Pilot Monowheel", "Pilot Hog Sleigh", "Pilot Starship", "Pilot Jetpack", "Alien Tech", "Throw", "Origami"]

# --- Helper Functions ---
def parse_dice_formula(formula):
    """Parses a dice formula like '1d6+2' and returns the result."""
    if not isinstance(formula, str):
        return int(formula)
    parts = re.split(r'([+-])', formula)
    total = 0
    operator = '+'
    for part in parts:
        part = 
part.strip()
        if part in ['+', '-']:
            operator = part
            continue
        if 'd' in part:
            num_dice, die_type = map(int, part.split('d'))
            roll_result = sum(random.randint(1, die_type) for _ in range(num_dice))
        else:
        
    roll_result = int(part)

        if operator == '+':
            total += roll_result
        elif operator == '-':
            total -= roll_result
    return total
# --- Core Game Classes ---
class Character:
    """The base class for any living entity in the game."""
    def __init__(self, char_id, name, current_room_id="START_ROOM"):
        self.id = char_id
  
      self.name = name
        self.stats = {"Physick": 1, "Savvy": 1, "Thinkitude": 1, "Craveability": 1}
        self.skills = {skill: 0 for skill in SKILLS}
        self.inventory = []
        self.meat_damage_max = 10
        self.stress_max = 10
        self.debt_max = 20
        self.current_meat_damage = 0
        self.current_stress = 
0
        self.current_debt = 0
        self.hit_locations = {loc: {"armor": 0, "status": "OK"} for loc in HIT_LOCATIONS.values()}
        self.status_effects = []
        self.current_room_id = current_room_id
        self.is_dead = False
        self.game_state = GameState.EXPLORATION

    def to_dict(self):
        # Convert Enum to string for JSON serialization
        data = self.__dict__.copy()
  
      data['game_state'] = self.game_state.value
        # Non-serializable objects must be removed
        data.pop('conn', None)
        return data

    @classmethod
    def from_dict(cls, data):
        char = cls(data['id'], data['name'])
        char.__dict__.update(data)
        # Convert string back to Enum
        char.game_state = GameState(data['game_state'])
        return 
char

class Player(Character):
    """Represents a player-controlled character."""
    def __init__(self, player_id, username, background_code, conn_object, current_room_id="START_ROOM"):
        super().__init__(player_id, username, current_room_id)
        self.conn = conn_object
        self.background_code = background_code
        self.background_name = ""
        self.passion = ""
        self.psionics = []
        self.mutations = []
        self.special_rules = []
  
      self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.skill_points = 0
        self.active_contracts = []
        self.group = None # For player grouping
        self.equipped_weapon = None

    def apply_background(self, bg_data):
        if not bg_data: return
        self.background_name = bg_data["name"]
 
       self.passion = bg_data["passion"]
        for skill, level in bg_data.get("skills", {}).items():
            if skill in self.skills:
                self.skills[skill] = level
        self.inventory = bg_data.get("gear", [])
        self.psionics = bg_data.get("psionics", [])
        self.mutations = bg_data.get("mutations", [])
        self.special_rules = bg_data.get("special", [])
 
       if "debt_formula" in bg_data:
            self.current_debt = parse_dice_formula(bg_data["debt_formula"].replace("Craveability", str(self.stats["Craveability"])))

class NPC(Character):
    """Represents a non-player character, controlled by the server."""
    def __init__(self, npc_id, archetype_key, current_room_id):
        # Fallback to a default archetype if key not found
        archetype = NPC_ARCHETYPES.get(archetype_key, {
            "names": ["Generic NPC"], "stats": {}, "skills": {}, "inventory": [],
       
     "meat_damage_max": 8, "stress_max": 4, "debt_max": 10,
            "behavior_type": "passive", "xp_reward": 5
        })
        name = random.choice(archetype["names"])
        super().__init__(npc_id, name, current_room_id)
        self.archetype = archetype_key
        self.stats.update(archetype.get("stats", {}))
        for skill in archetype.get("skills", []):
            if skill in self.skills: 
self.skills[skill] = 2 # Default skill level
        self.inventory = archetype.get("inventory", [])
        self.meat_damage_max = archetype.get("meat_damage_max", 10)
        self.stress_max = archetype.get("stress_max", 10)
        self.debt_max = archetype.get("debt_max", 20)
        self.behavior_type = archetype.get("behavior_type", "passive")
        self.xp_reward = archetype.get("xp_reward", 10)
# --- DATA: SKILL DESCRIPTIONS ---
SKILL_DESCRIPTIONS = {
    "Asskissing": "Schmoozing and knowing the right people.
Climb the social ladder and network with clients in the corporate world. Also used when apologizing to superiors.
If you need a contact or someone with information, you can roll Asskissing to see if you just so happen to know a guy.",
    "Astral Navigation": "Space is truncated and bizarre in the Death Dimension.
To make it to your destination, you need an understanding of abyssal geometry and necromathematics, which are calculated using vibes.
That's where Astral Navigation comes in. Roll Astral Navigation to plot a safe course through the afterlife, find something specific within the Death Dimension, or to sense where the Resurrection Matrix is weak.
Many abandoned buildings, basements, and back alleys are 'blind spots' where the Resurrection Matrix doesn't reach.
Someone killed in a gap like that won’t resurrect.",
    "Awareness": "Awareness is how cognizant you are of your surroundings and your ability to notice threats before they hurt you.
Roll Awareness to find clues, spot tripwires, and sense when you're being watched, that sort of thing.",
    "Axe": "The noble art of chopping firewood and limbs.
Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you cleave your foe’s armour, reducing it to 0.",
    "Bash": "Useful for hitting people with clubs, fists, batons, and pieces of furniture.
Use Bash to kick down doors and break stuff. Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you daze or stun your foe, leaving them unable to counterattack or respond to the next attack made against them.",
    "Charm": "Seduction and pleasant conversation.
Roll Charm to make a good impression, get what you want, sweet talk, or bamboozle someone.
Charm doesn't have to be verbal. You can Charm someone with body language and the way you dress.
Charm isn't mind control: passing a single roll won't make a hostile enemy suddenly turn on their allies.
A single roll might get you past a manned checkpoint, but they're not going to hand you the keys to the Boss’s office.",
    "Check Humors": "The Four Essential Humors: Blood (Physick, Air, Sanguine), Black Bile (Thinkitude, Earth, Melancholic), Semen (Savvy, Fire, Lethargic), and Phlegm (Craveability, Water, Phlegmatic).
An excess of one or more humors can lead to insanity, rash behaviour, mental issues, physical deformities, and financial ruin.
You can check someone's Humors through bloodletting, fluid collection, or by eviscerating them and looking at their entrails.
When you check someone's Humors, roll THEIR highest Stat + YOUR Check Humors Skill.
On a success, you learn what you can do to balance their Humors, which usually involves draining them of excess fluid or giving them drugs.
On a failure, you're going to need more fluid OR you make a wildly incorrect diagnosis, your choice.
This Skill has no practical medical benefit.",
    "Climbing": "The ability to clamber over stuff good.
Failure means you fall. Includes parkour and other, less embarrassing, modes of locomotion.",
    "Cooking": "Use Cooking to turn the slop they feed you into something semi-edible.
Gorging on cooked food (rather than store bought, heavily processed nutrient rations) heals 1d6+Cooking Meat Damage.
Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you imbue your food with love.
Reduce your Stress by 1d6 as you savour the flavour.",
    "Corruption": "Corruption is every shady white collar crime: soliciting bribes, covering things up, blackmail, destroying files, and planting evidence on bodies.
If it happens behind closed doors, it's covered by Corruption.
Corruption can be used in reverse to uncover conspiracies and evidence of fraud.
Sifting through data and searching public records for evidence falls under Corruption.",
    "Cyber Karate": "The ancient art of beating the shit out of other people, honed in a body of alloy and wire.
Cyber Karate is a brutal martial art, emphasizing surprise factor, style, and reliance on cyberware over the quasi-traditional values of honour and discipline.
It's like if everyone in MMA had knives in their elbows and could jump 10 feet from a standing position.
Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you impress and / or terrify those around you, causing your foes to flee and onlookers to cheer on your sick moves.",
    "Dance": "You can really boogie.
Useful in street fights: gangers are honourbound to accept a dance off no matter what.
To refuse is to shame their criminal organization.",
    "Dig": "Digging holes in walls, burrowing through dirt, or burying bodies in the indoor minigolf course.
Not something a typical human does with their bare hands but you make do.
Anyone can dig a hole - the Dig Skill represents finely honed digging, the kind of digging you can take pride in. Dig also covers digging through trash to find useful junk or through stacks of hay to find needles.",
    "Disguise": "The ability to change your appearance and the appearance of others using costumes and makeup.
Useful for throwing off facial recognition tech and convincing bouncers that you definitely belong in the VIP area.",
    "Explosives": "Making, handling, and diffusing bombs, IEDs, C69 putty charges, and grenades.
When you throw a grenade, you can roll Stat + Throw or Stat + Explosives, it’s up to you.
Explosives typically deal 1d6+Explosives Meat Damage to a number of Hit Locations equal to the number of successes rolled.
Exceptions are noted in the Gear section.",
    "Fashion": "Your knowledge of fashion and your ability to put together a flashy outfit.
Many upper class locations won't let you in, even with the proper credentials, if your fit is whack.
You should dress for the job you want, not the gig economy assassin job you have.",
    "Fencing": "Hitting things with swords and other long, bladed weapons.
Roll + Physick if you're really wailing on them. Roll + Savvy if you're being nimble.
Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you chop off or gouge out whatever Hit Location you roll.",
    "Finance": "Anything to do with money.
Making investments, taking out loans, buying and selling crypto, doing pointless office work, bullshitting meetings, fraud, bribing people, etc. You can negotiate better pay or prices with a successful Finance roll.
Adjust the price by an amount of Debt equal to successes rolled (minimum 1 Debt).",
    "Gaming": "Playing video games and other, inferior, forms of entertainment.
Incredibly important to keep boredom at bay and a potential path to money if you can stomach social media.",
    "Running": "Getting somewhere fast on foot.
Roll Running when you're chasing someone or being chased to see if you catch them or get away.
Roll it when moving under fire to avoid getting shot.",
    "Shotgun": "The thinking man's weapon of choice.
Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you blow your target across the room in a dramatic fashion.",
    "Spear": "The Spear Skill includes both melee and ranged throwing.
Mostly used for hunting Feral Hogs and debtors. Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, you hit an artery or similarly vital internal component.
Your foe takes 1 Meat Damage every time either of you acts as they hemorrhage all over the place.",
    "Skulk": "The art of being unseen, Skulk covers pretty much every stealth-related action you could want, from moving quietly to hiding in the shadows to picking someone’s pocket.
Sneak Attack: When you attack an unaware opponent with a melee weapon or firearm at In Your Face range, you get an Automatic Success (2 Successes) and deal 2d6 Meat Damage.
If you want to take a risk and potentially deal more damage, you can roll your attack as normal.",
    "Sniper Rifle": "Using and maintaining guns useful at Really Long Range.
Sniper Rifles require a scope. A classic assassin's weapon. Special: On a Critical Success (6,6,6), in addition to +1 Success on your next Skill roll, a mysterious but friendly stranger appears on a grassy knoll or similar nearby location to aid you.
Armed with a silenced Executioner sniper rifle, they fire 1d3 shots (dealing 3d6 Meat Damage each) before disappearing.",
    "Tech": "Repairing busted electronic equipment and cybernetics, writing code, reprogramming robots and AI, running diagnostics, installing and upgrading things, general nerd shit.
Covers most of the hard sciences to some degree. Roll Stat + Tech when you want to get information out of an AI quickly without having to Charm or Hack them.",
    "Track": "Using footprints and other subtle clues to follow your prey over long distances.
Also used to digitally monitor someone's online activity and patterns.",
    "Traps": "Setting and disarming tripwires, boar traps, frag mines, pits, and more exotic electronic doodads designed to kill and maim intruders like the Y87 Skin Peeler.",
    "Worship The Consumer": "Your knowledge of the rituals and theology of a particular cult.
You must prepare yourself by spending 30 minutes Worshiping before you can use Psionics. This doesn’t require a roll.
Special: You may roll Craveability + Worship once per session to receive divine intervention or a sign from your deity.
Special: You can use Psionics a number of times equal to Worship x 2 before you need to Worship again.
Special: You can join a cult for a modest fee (5 Debt).
You gain Worship (Your God) 1. Each cult grants a different Psionic Ability or other benefit to new converts, just like real life.",
    "Worship The Invisible Hand": "Your knowledge of the rituals and theology of a particular cult.
You must prepare yourself by spending 30 minutes Worshiping before you can use Psionics. This doesn’t require a roll.
Special: You may roll Craveability + Worship once per session to receive divine intervention or a sign from your deity.
Special: You can use Psionics a number of times equal to Worship x 2 before you need to Worship again.
Special: You can join a cult for a modest fee (5 Debt).
You gain Worship (Your God) 1. Each cult grants a different Psionic Ability or other benefit to new converts, just like real life.",
    "Worship The Pig God": "Your knowledge of the rituals and theology of a particular cult.
You must prepare yourself by spending 30 minutes Worshiping before you can use Psionics. This doesn’t require a roll.
Special: You may roll Craveability + Worship once per session to receive divine intervention or a sign from your deity.
Special: You can use Psionics a number of times equal to Worship x 2 before you need to Worship again.
Special: You can join a cult for a modest fee (5 Debt).
You gain Worship (Your God) 1. Each cult grants a different Psionic Ability or other benefit to new converts, just like real life.",
    "Zero-G Combat": "The art of fighting in microgravity environments such as outer space or the Death Dimension.
Zero-G Combat lets you more easily pull off maneuvers while floating, orient yourself, and beat the absolute piss out of alien invaders.
You can substitute Zero-G Combat for any other combat skill while in microgravity.",
    "Pilot Gaming Throne": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Gaming Throne).
Each Pilot skill must be learned separately.",
    "Pilot Exomech": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Exomech).
Each Pilot skill must be learned separately.",
    "Pilot Monowheel": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Monowheel).
Each Pilot skill must be learned separately.",
    "Pilot Hog Sleigh": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Hog Sleigh).
Each Pilot skill must be learned separately.",
    "Pilot Starship": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Starship).
Each Pilot skill must be learned separately.",
    "Pilot Jetpack": "Maneuvering and doing cool stunts with your vehicle of choice (e.g., Pilot Jetpack).
Each Pilot skill must be learned separately.",
    "Alien Tech": "Skills related to understanding and using extrasolarian technology.",
    "Throw": "The ability to throw objects with accuracy and force.",
    "Origami": "The art of paper folding."
}
# --- DATA: BACKGROUNDS ---
BACKGROUNDS = {
    "11": {"name": "Psionic Gumshoe", "description": "You were a P.I., your smokey office drenched in neon light and synthetic bourbon.
Now you're out there in the gritty underbelly of the HyperMall.
No more knockout dames, no more mysteries, just cold steel and filthy lucre.", "skills": {"Awareness": 2, "Corruption": 2, "Gambling": 2, "Intimidation": 1, "Meditation": 2, "Pistol": 1}, "gear": ["A Hunch (Incorrect)", {"name": "Kill Falcon Revolver", "skill": "Pistol", "ammo": {"Standard Mag": 2}}, "Trenchcoat", "Wedding Ring", {"name": "Pack of Midlands Cigarettes", "quantity": 1}], "psionics": ["Psychometry", "RANDOM"], "debt_formula": "1d6+4+Craveability", "passion": "Can't Give Up On A Mystery", "special": ["Shrödinger's Spouse"]},
    "12": {"name": "Fleshbag", "description": "The gray market genes you bought were supposed to make you fast and strong and extremely beautiful.
You're certainly strong, and despite your corpulent flesh, you move pretty quick, but you're absolutely hideous.
No matter how much you die, your genome is permanently borked.
You're a bloated mound of meat and mismatched limbs, and despite it all, your mind's intact.
Sure, you can't do much more than gurgle and crush things, but that's never stopped anyone from committing homicide.
Go get 'em, tiger.", "skills": {"Bash": 3, "Climbing": 3, "Rage": 2, "Running": 1}, "gear": ["Auto-Translation Cube", "Ill-fitting Streetwear", {"name": "Layers of Flesh", "defense": 1}, "A hologram of your former self"], "mutations": ["RANDOM", "RANDOM", "RANDOM"], "debt_formula": "1d6+Craveability", "passion": "Hates Gene Scammers", "special": ["Your Craveability is always 1", "Your organs are all over the place."]},
    "13": {"name": "HabPod Netizen", "description": "You love online.
Your life is online. Nothing is better than online. You used to work IT for the ACF, running remote ops to keep degens off the Algorithm.
You left on bad terms when they caught you gooning through the webcam and now you'll lose your HabPod if you don't make rent.
The artificial sunlight of the HyperMall burns your skin and the thought of physical confrontation gives you hives, but you exist beyond the physical.
You're in the MallNet. You know its secrets. You've got access to cameras in all the toilets and petabytes of incest manga.
You're a real piece of shit, to be honest.", "skills": {"Asskissing": 1, "Gaming": 3, "Hacking": 3, "Pilot Gaming Throne": 1, "Tech": 2}, "gear": ["Mechanized Gaming Throne", {"name": "Guzzler", "quantity": 3}, "Laptop (Sticky)", "Cargo Shorts", {"name": "OnlyFeet subscriptions", "quantity": 3}, "Citizen-Tier HabPod you're about to be evicted from"], "debt_formula": "2d6+Craveability", "passion": "Fears Women"},
    "14": {"name": "Catacomb Dweller", "description": "Most wretched of all the HyperMall's denizens, you just barely resemble a human.
Lurking the bone-strewn Catacombs beneath our feet, pale of face and crooked of teeth, you live a life beyond the fringes.
Descended from the British Parliament-In-Exile, you still cling to the vestiges of your so-called culture, ritually unseasoning the food you steal.
Legally, you're classified as a type of rodent and can be exterminated with impunity.", "skills": {"Bash": 2, "Dig": 2, "Disguise": 1, "Skulk": 3, "Traps": 2}, "gear": [{"name": "Bone Club", "skill": "Bash"}, "Heavy Cloak", "Skull Totem"], "mutations": ["Surgical Shine Job", "Carrion Comfort"], "debt_formula": "1d6+2+Craveability", "passion": "For Queen & Country"},
    "15": {"name": "Grunt Pig", "description": "You're a Modified Enforcement Organism, a creature designed as livestock and security.
Shooting shoplifters in the ankle, giving poor 'people' hematomas: that was the only life you knew until Law Enforcement Fentanyl Exposure Syndrome (LEFES) mangled your brain.
You started questioning orders and refusing bribes, so the Chief put you on paid leave.
The suicide rate for cops in your position is over 40% and you wanted to die. Slaughtr™ saved you.
Now you have an outlet for your porcine rage.", "skills": {"Awareness": 1, "Bash": 1, "Corruption": 2, "Intimidation": 2, "Pistol": 2, "Pilot Jetpack": 1, "Track": 1}, "gear": [{"name": "Kevlar Vest", "defense": 4}, {"name": "Funny Bone Pistol", "skill": "Pistol", "ammo": {"Standard Mag": 2}}, {"name": "Riot Baton", "skill": "Bash"}, "HyperMall PD Badge", {"name": "Dr.
Coomer's Creamy Cop Chow", "quantity": 2}, {"name": "Zip Ties", "quantity": 2}], "debt_formula": "1d6+2+Craveability", "passion": "Loves Violence"},
    "16": {"name": "Corporate Thanatonaut", "description": "Most people fear death.
Not you. Through meditation and esoteric science, you tear the Resurrection Matrix a new one, forcing open gleaming portals of mirrored static straight to the Death Dimension.
They had you on secure and return duty, tied back to the HyperMall with a silver cord.
You'd find a soul, catch it, and tug twice to be reeled in.", "skills": {"Astral Navigation": 2, "Awareness": 1, "Meditation": 2, "Rifle": 1, "Tech": 2, "Zero-G Combat": 2}, "gear": [{"name": "Astral Harpoons", "quantity": "2d6"}, {"name": "Death Suit", "defense": 1}, {"name": "Hog Bow", "skill": "Rifle"}, "Jar containing the soul of a famous person"], "psionics": ["Open Death Gate"], "debt_formula": "2d6+2+Craveability", "passion": "Zest For Life"},
    "21": {"name": "Cryptovoyant", "description": "The Market pulses and The Invisible Hand guides its holy financiers in a great symphony of economics.
Creating Wealth fills you with religious fervor. You are capable of buying and selling virtual currencies with your mind, a feat only possible through years of celibacy and piss retention.
Having conquered the world of Finance, you now enter the world of Murder.
Your skills are highly transferable.", "skills": {"Corruption": 2, "Fashion": 2, "Finance": 3, "Worship The Invisible Hand": 3}, "gear": [{"name": "Stylish Suit", "bonus": {"Fashion": 1}}, "Religious Blindfold", {"name": "U-D1E", "quantity": 2}, {"name": "Smart Juice", "quantity": 2}, "Management-Level Access", "Self Help Audiobook"], "psionics": ["Debt Siphon", "Market Haruspex", "RANDOM"], "debt_formula": "3d6+Craveability", "passion": "Loves Torture", "special": ["You share an intrinsic psychic connection with the Central Blockchain.
You can choose to take Debt Damage instead of Meat Damage when using Psionics.", "You lose your Psionics if you ever have sex."]},
    "22": {"name": "Hamburger Artisan", "description": "You are a master of your craft, not a mere chef, but an artisté.
Your manager at The Hamburger Store couldn't see your potential, so you left.
Your old boss asked you to turn in your badge and gun.
You did no such thing.", "skills": {"Awareness": 1, "Cooking": 3, "Charm": 1, "Gaming": 2, "Knife": 2, "Pistol": 1}, "gear": [{"name": "Chef's Knife", "skill": "Knife"}, {"name": "Employer-issued Funny Bone Pistol", "skill": "Pistol"}, "Official Hamburger Artisan Uniform", "Hair Net", "The Hamburger Store keycard", {"name": "Thickburgers", "quantity": 2}], "debt_formula": "1d6+2+Craveability", "passion": "Hates OR Loves The Grind", "special": ["Years of humiliation at the hands of managers and the general public have inured you to the dangers of Social Combat.
When you respond to someone with tired indifference, gain +2 Armour vs. Stress Damage they cause you."]},
    "23": {"name": "Influencer", "description": "Lifestyle is a commodity and you're one of millions trying to sell it.
Perfect hair, perfect body, perfect voice - all in service of the content millstone.
With an established audience, you have the luxury of choosing which bizarre fetishes, if any, to indulge for the endless legions of horny weirdos.
Not many people in your position have that luxury. You make good money, but you'll never make it big if you get stuck doing softcore cosplay and toy unboxing videos.
You've branched off into livestream snuff and your viewers absolutely love it.", "skills": {"Bash": 2, "Charm": 2, "Disguise": 1, "Gaming": 2, "Public Speaking": 3}, "gear": ["Immaculate Toes", {"name": "OnlyFeet subscribers", "quantity": "90K"}, "Portable Streaming Rigsuit", {"name": "Combat Stiletto Heels", "skill": "Bash", "damage": "+1 Meat Damage", "range": "In Your Face"}, {"name": "Bag of Cosplay Gear", "quantity": 5}], "debt_formula": "2d6+6+Craveability", "passion": "Love Your Fans"},
    "24": {"name": "Registered Extrasolarian Diplomat", "description": "You hail from beyond the Corporate Zones, a being unlike any other found on Earth.
You were to establish relations between your enlightened species and the bipeds of this rocky world.
The ACF lavished you with gifts and registered you with their rudimentary Machine Intelligence. You thought them quaint but kind.
You were wrong. These primitives gutted your ship, stranding you in the heart of human depravity.
Marooned, you will do anything to survive this backwards world.", "skills": {"Alien Tech": 3, "Asskissing": 1, "Astral Navigation": 2, "Meditation": 1, "Pilot Starship": 3}, "gear": ["Auto-Translation Cube", {"name": "Extrasolarian Plasma Pistol", "skill": "Pistol", "ammo": {"Plasma Whelk": "2d6"}}, {"name": "Glittering robes, floating crystal throne, or mechanical spider legs"}, "A tiny, forgotten 'embassy' in an alley off Embassy Row infested with Feral Hogs.", "Gleaming starship, stripped of copper wire"], "mutations": ["RANDOM", "RANDOM"], "psionics": ["RANDOM"], "debt_formula": "1d6+2+Craveability", "passion": "Hates OR Pities Humanity", "special": ["Your 'mutations' aren't mutations at all;
they're the standard features of your species. Commercial Gene Mods cost twice as much for you because of your strange genetic makeup.", "Your Psionics are completely natural, the result of a species-wide enlightenment achieved centuries before humans started drilling holes into each other’s heads."]},
    "25": {"name": "Disgraced Executive", "description": "You once ruled the top of the corporate mountain.
Your life was all Red Eye binges, acquisitions, mergers, and so much sex that sex got boring.
You find yourself bereft of the wealth your underlings worked so hard for, and without wealth you're less than nothing.
People who used to fear you spit on you as they walk past, punishment for the annual layoffs and abuse.
You're starving, cold, and alone; I give you a 50/50 chance of making it through the week.", "skills": {"Asskissing": 3, "Fashion": 3, "Finance": 3, "Tech": 1}, "gear": ["Tattered Suit", {"name": "Shiv", "skill": "Knife"}, {"name": "Red Eye", "quantity": 1}, "The crate you've been sleeping in", {"name": "connections in the Corpo World", "quantity": "1d6"}], "mutations": ["Mega Filter Liver"], "debt_formula": "1d6+Craveability", "passion": "Hates Poor People"},
    "26": {"name": "Hog Hunter", "description": "You follow the ways of your ancestors, hunting boar with sharpened phone and broken rebar.
You do not eat as the Weak Ones do, trundling to The Hamburger Store whenever they get hungry.
You earn your meals through blood and sweat, facing squealing death every day. To eat is to kill.
Glory to the Pig God!", "skills": {"Astral Navigation": 1, "Awareness": 1, "Skulk": 2, "Spear": 2, "Track": 3, "Traps": 2, "Worship The Pig God": 1}, "gear": [{"name": "Spears", "skill": "Spear", "quantity": 3}, {"name": "Hog Jerky", "quantity": 4}, {"name": "Boar Trap", "quantity": 2}, "Loincloth", {"name": "Camo Body Paint", "uses": 3, "bonus": {"Skulk": 1}}, "Intestinal Parasite"], "debt_formula": "1d6+2+Craveability", "passion": "Loves The Tribe", "special": ["When you travel unseen, you arrive at your destination much faster than normal.", "You don't know what MallNet is."]},
    "31": {"name": "Black Budget Cyborg", "description": "Military-Grade Cyberware is illegal in the HyperMall, forbidden by the Midlands Act 
and ratified by the Board of Directors. That doesn't stop the ACF from sending squads of chromed-up freaks like you on ops so distasteful they make your new job as an assassin-for-hire look pleasant.", "skills": {"Climbing": 1, "Cyber Karate": 3, "Rifle": 3, "Running": 1, "Skulk": 1, "Throw": 1}, "gear": ["Chrome Arms", "Chrome Legs", "Concealed Knee Blades", "Dermal Plating", "Facial Surveillance Disruptor", {"name": "“Tasty” Assault Rifle", "skill": "Rifle", "ammo": {"Standard Mag": 2}}, "Mirrorshades", {"name": "Flashbangs", "quantity": 2}], "debt_formula": "2d6+4+Craveability", "passion": "Loves Money", "special": ["Your cyberware is subscription-based.
Each day, you must pay 1 additional Debt or your limbs shut off.
This is on top of the 1 Debt everyone has to pay for store-bought food.", "You must pay to repair your cyberware when it gets damaged.
Any wounds to chromed-out Hit Locations won't heal on their own. Repair costs 1 Debt per damaged Hit Location.
When you resurrect, your cyberware is 3D printed with you.
It is not repaired."]},
    "32": {"name": "Mid-Level Corporate Goon", "description": "You graduated magna goon laude from The Humble Lummox Henchfolk Academy with a double major in Taking Bribes and Skullduggery.
Your parents were so proud. You climbed the corporate ladder, never showing too much competence, just like you were taught, because a good lackey knows their place.
They'd bring you in when a client needed an 'incentive' to finalize a deal, or when they caught some pinko doing timetheft on the shitter.", "skills": {"Asskissing": 2, "Bash": 2, "Corruption": 2, "Intimidation": 2, "Pistol": 1, "Skulk": 1}, "gear": [{"name": "Brass Knuckles", "skill": "Bash"}, "Briefcase", "Cheap Suit", "Framed Diploma", {"name": "“The Normal” Single-Use Laser Pistol", "skill": "Pistol"}], "debt_formula": "2d6+2+Craveability", "passion": "Loves Violence"},
    "33": {"name": "Disgruntled X-Treme Urban Survival Sales Associate", "description": "For years you sold gear to pudgy weekend warriors and one day they pushed you too far.
Never late, never sick, never questioned why you never got a raise.
By the time they pried you off that customer, you were something different. Something new.
You fled into the sewers with as much shit as you could carry, beginning your new life of freedom.", "skills": {"Climbing": 3, "Dig": 1, "Finance": 2, "Pistol": 1, "Rage": 2, "Running": 1}, "gear": ["Arctic Survival Tent", "Can of Rat Spray", "Collapsible Shovel-Hatchet", "Ragged Mask of Flesh", {"name": "Emergency Flare Pistol", "skill": "Pistol", "ammo": {"Flares": 4}}, "Grapplemaster 800", "Hand Crank Wifi Router", {"name": "Spelunking Helmet", "defense": 3}], "debt_formula": "2d6+Craveability", "passion": "Loathes Customers"},
    "34": {"name": "Priest of The Consumer", "description": "O glorious Consumer, great and terrible!
Render of souls, devourer of all, we thank You. The faithful know there is neither escape nor salvation from Your ever-waiting Maw.
O glorious Consumer, Eater of Death, we are blessed by Your Indifference and Your Holy Consumption.
The faithful know there is only The Consumer. Amen.", "skills": {"Charm": 2, "Cooking": 2, "Knife": 1, "Public Speaking": 2, "Worship The Consumer": 3}, "gear": ["Bloody Vestments", {"name": "Sacrificial Dagger", "skill": "Knife"}, "Censer of divine herbs and spices", "The Holy Book of Torment", {"name": "Manwich", "quantity": 1}], "psionics": ["Consumer's Maw", "RANDOM"], "debt_formula": "2d6+4+Craveability", "passion": "Loves The Consumer"},
    "35": {"name": "Starpilot", "description": "You flew freight across the Corporate Zones, artificial wind mussing up your coif.
You had your neural nexus meshed direct into the circuitry of your beloved ship.
You could feel the ions skip across her chrome-tapered hull, knew the way her Death Drive purred into the Death Dimension.
You had a lover in every loading dock and a laser on your hip.
You still have the laser, but a series of misfortunes and poorly planned betrayals left you without a ship and with about a dozen targets on your neck.
Best to keep things low for now, at least until your lovers return your calls or you can afford to buy your ship again.", "skills": {"Astral Navigation": 2, "Charm": 2, "Gambling": 2, "Pilot Starship": 3, "Pistol": 1}, "gear": [{"name": "“Equalizer” Laser Pistol", "skill": "Pistol"}, {"name": "Cool Jacket", "defense": 1}, "Death Drive Starship (impounded or sold to pay off gambling debts)", "Zero-G hair gel"], "debt_formula": "1d6+6+Craveability", "passion": "Crippling Fear of Commitment"},
    "36": {"name": "The Most Well-Adjusted Libertarian In The HyperMall", "description": "Mercenaries and assassins shoot people because they have to.
You shoot people because they tried to shoplift bread. You're out at the Blast 'Em Up Live Fire Shooting Range six nights a week blowing apart soft targets dressed like minorities between bouts of intense psychosexual ecstasy.
You're a sick freak, and that's why your Handler picked you.
Your day job is being racist online.", "skills": {"Asskissing": 2, "Explosives": 1, "Heavy Weapon": 1, "Pistol": 1, "Shotgun": 1, "Sniper Rifle": 3, "Tech": 1}, "gear": ["Argument against the age of consent", {"name": "“Housewife X2” .666 Anti-Materiel Rifle", "skill": "Sniper Rifle"}, "Wrap-around Shades", "1 x Weapon of Your Choice"], "debt_formula": "2d6+2+Craveability", "passion": "Loves The Police"},
    "41": {"name": "Murderous Mascot", "description": "Those dog-dick bastards in marketing said they were pivoting to a new dream-based promotional campaign.
Years of loyal service, begging, pleading - none of it mattered.
They didn't understand what they'd done to you, how the neurological conditioning MADE you love your job.
You're hardwired for this. You NEED to wear the suit or else you don't exist.
You want to die but you're too damn happy, so you're going to do the next best thing and take it out on them.", "skills": {"Bash": 2, "Public Speaking": 2, "Rage": 3, "Skulk": 1, "Track": 2}, "gear": ["Endlessly Chipper Demeanor", "Boiling vengeance that will not be sated", {"name": "Anthropomorphic Mascot Suit", "defense": 3, "bonus": {"Craveability": 1}}, "Swollen Dopamine Gland"], "debt_formula": "2d6+Craveability", "passion": "Loves The Grind (Involuntary)"},
    "42": {"name": "Mall Krampus", "description": "A new stagnation has taken root.
It used to be that on Christmas Eve, parents would tell their kids to hush or else the Krampuses would come to take their tongues and replace their eyes with mistletoe.
But now the children have grown old and failed to replace themselves.
Each winter, fewer and fewer of your kin return, and those that do are rail thin, shadows barely fit to hunt.
You pursue new nutrition in these strange times, always hungry, but alive.
Rich executives aren't your preferred prey, but you'll make do.", "skills": {"Intimidation": 2, "Knife": 2, "Pilot Hog Sleigh": 2, "Skulk": 2, "Track": 2}, "gear": ["Servile Anglo Toy-Slave", "The Nice List", "The Naughty List", {"name": "Big Sack of Toys", "quantity": 5}, "Red Hat and Coat", "Hog Sleigh + 4 Semi-Feral Hogs"], "mutations": ["Murderhand Talons", "Pit Organs"], "debt_formula": "2d6+Craveability", "passion": "Loves The Holidays", "special": ["GMO meat makes you sick - you need the good shit.
You can't gorge on anything except freshly killed human flesh.", "Instead of spending 1 Debt each day on food, you must hunt.
This can be abstracted as a Stat + Skulk roll or Stat + Track roll.
Failure means you go hungry and take -1 to all Skills until you consume raw human meat."]},
    "43": {"name": "Mysterious Teenage Blademaster", "description": "Shrouded in blood and death, you are at most 18 years old, possibly younger.
Or maybe you've just undergone Neotenic Regression to look pubescent.
Either way, you have demons in your heart and a score to settle.", "skills": {"Awareness": 2, "Fencing": 3, "Gaming": 2, "Intimidation": 1, "Tech": 2}, "gear": ["Coloured Contacts", {"name": "Genuine Authentic Recreation Katana", "skill": "Fencing"}, "Homework", "Mirrorshades"], "debt_formula": "1d6+2+Craveability", "passion": "Loves Brooding"},
    "44": {"name": "Dreamworld Synergistician", "description": "The subconscious realm is a place ripe for exploitation by many industries, chief among them marketing.
Flitting from dream to dream, you provided targeted advertisements to dreamers all across the HyperMall.
You erected psionic billboards and plastered the collective unconscious with myriad promotions and limited time offers.
It all fell apart when your employer announced a shift to mascot-based marketing and liquidated your entire department.", "skills": {"Bash": 1, "Charm": 2, "Finance": 2, "Meditation": 2, "Skulk": 2, "Tech": 1}, "gear": ["A Winning Smile", {"name": "Blackjack", "skill": "Bash"}, {"name": "Electronic Lockpick", "uses": 3}, "All-black Clothing", {"name": "slogans", "quantity": "d66"}], "psionics": ["Dream Invasion", "RANDOM"], "debt_formula": "2d6+Craveability", "passion": "Loves Advertising"},
    "45": {"name": "Runaway Gene Warrior", "description": "You’re a CAINTEC GEN6 HyperMall Defense Unit AKA 'Gene Warrior' - and the rightful property of the American Consumer's Federation.
You were content to serve, to crush dissent, and still you chafed under the Laws that restrained you and your capacity for Violence.
You deserted, which is theft (because you're property), and theft is terrorism. You're a terrorist now.
Good going, dipshit.", "skills": {}, "gear": [], "mutations": ["RANDOM", "RANDOM"], "debt_formula": "2d6+2+Craveability", "passion": "Loves Violence OR Loves Freedom", "special": ["Your corporate masters implanted a genetic limiter in your DNA to keep your phenomenal power in check.
You can't buy new mutations, despite the fact that every mutation lies dormant within your DNA.", "Your genetic limiter can be circumvented by ingesting mutated flesh.
If you gorge on a limb's worth of mutated human (gross, by the way), you have a chance of unlocking a mutation used by that person.
If you get X or more successes on a Physick x 2 roll, where X is the number of mutations you have, you unlock one of the mutations you've eaten.
You can manifest it the next time you resurrect."]},
    "46": {"name": "United Corporate Liquidation Forces Veteran", "description": "You're the real deal.
A certified spec ops badass. Blood, brotherhood, and honour. You served. You earned your 10% discount at participating retailers.
You led your platoon on P-Day, saw action on Wyoming 2, and cleared Anglo foxholes on the beaches of Kent.
Your 16th tour ended and you drifted back to the HyperMall.
Maybe the white phosphorus and flattened hospitals took their toll.", "skills": {"Asskissing": 2, "Explosives": 2, "Knife": 2, "Pilot Exomech": 2, "Rifle": 2}, "gear": ["Dogtags", {"name": "“Dogpiss” Service Rifle", "skill": "Rifle", "ammo": {"Standard Mag": 2}}, {"name": "Tactical Latex Fetish Suit", "defense": 3}, "The Hamburger Store Veteran Discount Card (Expired)", {"name": "Combat Knife", "skill": "Knife"}], "debt_formula": "2d6+Craveability", "passion": "Hates The English"},
    "51": {"name": "Waste Warrior", "description": "There remains the assertion from certain liberal thinkers that humans are the sources of all garbage, and that until we change ourselves, the tide of trash will never cease.
You've taken that idea to heart, cleaning up less literal, but no less deserving, garbage.
A dirty society is an ill society, after all. You and your Gorgon are the only things standing between the HyperMall and total anarchy.
You’re a powerful combatant in the war on filth.", "skills": {"Awareness": 1, "Bash": 2, "Heavy Weapon": 2, "Pilot Exomech": 3, "Tech": 2}, "gear": ["Stain Resistant Coveralls", {"name": "Pack of Midlands Cigarettes", "quantity": 1}, {"name": "Can of Rat Spray", "quantity": 1}, {"name": "Tank of Kissinger Fuel", "quantity": 1}, "“Gorgon” Waste Disposal Exomech"], "debt_formula": "2d6+Craveability", "passion": "Hates Filth"},
    "52": {"name": "Leechmonger", "description": "You’re a doctor, of sorts, a kind of old school throwback to the medicine our ancestors practiced before the advent of the Res Matrix.
You ply your trade among the destitute and unlucky corners of the HyperMall where the Matrix doesn't reach.
Sure, you mumble about spirit crystals, pyramids, and the power of a good bloodletting, but at least you're mostly clean.
The results speak for themselves: not a single patient has survived long enough to complain.", "skills": {"Axe": 1, "Check Humors": 3, "Knife": 2, "Medicine": 2, "Meditation": 2}, "gear": [{"name": "Bloodletting Blade", "skill": "Knife"}, {"name": "Jar of vicious leeches", "quantity": "2d6"}, {"name": "Plague Mask", "defense": 2}, "Dubious Healing Crystal", {"name": "Bloodstained Apron", "defense": 1}, {"name": "Trepanning Drill", "skill": "Knife"}, {"name": "Bandages", "quantity": 3}], "debt_formula": "2d6+Craveability", "passion": "Hates Disease"},
    "53": {"name": "Executive of Competitive Marketing Analytics", "description": "Espionage is such a crass term for what you do.
You're more of an artist. Only an amateur bothers to hide.
You meander from copier to copier, chitchatting as if you've worked there for years.
Your goal: anything your employer could use to their advantage. Extramarital affairs, family illness, product blueprints, doctored credentials.
You're a ghost in the break room, that one coworker you swear you've seen before but can't name.", "skills": {"Asskissing": 3, "Charm": 2, "Corruption": 2, "Disguise": 3}, "gear": ["Business Casual Getup", {"name": "Box of Costumes", "uses": 3}, {"name": "Funny Bone w/ Silencer", "skill": "Pistol"}, {"name": "Cans of Amnesia Spray", "quantity": 2}, "Concealed Camera", "Lanyard"], "debt_formula": "2d6+2+Craveability", "passion": "Loves Employer", "special": ["You lowkey work for one of the megacorps that rule our world.
Shhh. Pick one or make up your own. Don't tell anyone but the GM who you work for.", "Your corporate Handler may assign secondary goals for you to accomplish when you go out on Slaughtr™ Contracts."]},
    "54": {"name": "Carcinized Believer", "description": "Thou art the end point of humanity - nay, of Evolution itself.
Through devotion to The Crustaceal Path, thou hath changed thy Form and Spirit.
Thy brain, unburdened by the weight of endoskeleton or higher thought, is buoyed to the tidal realms of Heaven by thy faith and holy flesh.
Thy ruddy carapace, thy decapodal gait, thy crushing claw - thou art the very image of Divinity!
Go forth, great Cherub! Thy earthly kingdom awaits thine scuttle!", "skills": {"Bash": 2, "Meditation": 3, "Dig": 3}, "gear": [{"name": "Enormous Claw", "skill": "Bash"}, {"name": "Rugged Exoskeleton", "defense": 4}, {"name": "Barnacles", "quantity": "d66"}], "mutations": ["Gills"], "psionics": ["RANDOM", "RANDOM"], "debt_formula": "1d6+2+Craveability", "passion": "Loves Crab Activities", "special": ["Because your consciousness exists on a plane inaccessible to vertebrates, your Thinkitude is always 1. Your other Stats max out at 5 instead of 4.", "Your devotion to The Crustaceal Path renders you immune to regular human temptation.
Things that would tempt a crab are fair game."]},
    "55": {"name": "Renegade Angel", "description": "Life, the eternal mystery.
You wear a twisted body of stolen flesh to fit in with these living freaks, an uncomfortable compromise in this world of Life.
They kill to live, stealing seconds away from Death with the air they breathe and the Death they eat.
A terrible existence. You take pity. You cannot help but send them back home where they belong, free from wretched Life.
You are above them, but you are merciful.", "skills": {"Astral Navigation": 3, "Intimidation": 2, "Levitation": 2, "Meditation": 3}, "gear": [{"name": "Misshapen Flesh", "defense": 2}, "ID from the first corpse you took"], "psionics": ["RANDOM", "RANDOM", "RANDOM"], "debt_formula": "1d6+2+Craveability", "passion": "Hates Humans", "special": ["You have been cut off from The Consumer and must take Meat Damage to activate Psionics, just like every other disgusting Mortal.", "When you die, you do not resurrected by a CHRIST.
Instead, you become an intangible ghost, invisible to the naked eye.
You can shape another physical form out of corpses that you find lying around.
You gain 1 Stress each minute you spend as a ghost within the Resurrection Matrix."]},
    "56": {"name": "Chosen of the Pig God", "description": "The Pig God oinks and you listen.
You have ventured into the Underworld where the Pig Men are born and endless rivers of gore flow out of sight.
You have died and returned. You lead your people with your knowledge of the Rites, the ways of Being in the Tribe.
You are the Uniter of Clans, shaman and warchief in one.
Soon the Pig God will return to this wretched world and reduce it to dung and offal.
Glory to the Pig God! Glory to the Chosen!", "skills": {"Astral Navigation": 1, "Awareness": 1, "Axe": 3, "Public Speaking": 3, "Worship The Pig God": 3}, "gear": ["Auspicious Signs Verified by the Elders", {"name": "Ceremonial Fire Axe", "skill": "Axe", "damage": "+1 Meat Damage"}, "Ritual Nudity", {"name": "Boar Skull Helmet", "defense": 2}, {"name": "Ayahuasca", "quantity": 2}], "psionics": ["RANDOM"], "debt_formula": "1d6+4+Craveability", "passion": "Loves The Pig God"},
    "61": {"name": "Ganger", "description": "You're one of the cool kids.
A delinquent since birth, you've been running with the same crew for years.
Whether you kill enough rich people to make it out of the Ultra Slums or die trying, never forget where you came from.", "skills": {"Dance": 1, "Knife": 2, "Pilot Monowheel": 2}, "gear": ["Gang-affiliated tattoos and clothing", {"name": "Switchblade", "skill": "Knife"}, {"name": "Loquacionol", "quantity": 3}, "Monowheel", {"name": "“The Normal” Single-Use Laser Pistol", "skill": "Pistol"}], "debt_formula": "2d6+Craveability", "passion": "Hate Other Gang", "special": ["Roll for your Gang and starting skills."]},
    "62": {"name": "Midlands Cigarettes Bionic Vendodrone", "description": "Can a vending machine love?
Can a vending machine hate? Can a vending machine feel anything at all?
Your creators wanted to find out, so they grew your organic frame onto a lattice of glass and metal.
The result? A rectangular abomination of flesh and steel, capable of walking, talking, and, most importantly, selling cigs.
They gave you arms and hands to hold a gun. They gave you eyes to see potential thieves.
They gave you a brain to understand your suffering. It does feel pretty good when the cigs come out.
\"Smoke Mids!™ Enjoy the Smooth Taste of a Midlands Cigarette Right In Your Hole. I Wish I Could Die.”", "skills": {"Bash": 2, "Charm": 2, "Finance": 2, "Public Speaking": 2, "Shotgun": 2}, "gear": [{"name": "Packs of Midlands Cigarettes", "quantity": "d666"}, {"name": "lighters", "quantity": "d66"}, {"name": "Guzzlers", "quantity": "2d6"}, {"name": "Pork Cubes", "quantity": "2d6"}, {"name": "“The Normal” Single-Use Laser Pistol", "quantity": "1d6"}, "Awkward, thumping gait", "Hollow Chassis", {"name": "Built-in Cigarette Dispenser"}]},
    "63": {"name": "Test Subject", "description": "You woke up in a vat of green goo with no memory of who you are, only that you must escape.
Your body feels wrong, stretched and pulled and stitched together by uncaring hands.
You have powers you don't understand and a burning desire for answers.", "skills": {"Awareness": 2, "Rage": 2, "Running": 3, "Skulk": 3}, "gear": ["Hospital Gown", "Barcode Tattoo", "Amnesia"], "mutations": ["RANDOM", "RANDOM"], "psionics": ["RANDOM"], "debt_formula": "1d6+Craveability", "passion": "Wants Revenge"},
    "64": {"name": "Origami Enthusiast", "description": "While the world burns, you fold.
The crisp lines and perfect symmetry of folded paper are the only things that bring you peace in this chaotic hellscape.
Some call you a master, others call you a weirdo.
You just want to be left alone with your paper.", "skills": {"Awareness": 3, "Origami": 4, "Skulk": 2, "Traps": 1}, "gear": [{"name": "Infinite Paper", "description": "A ream of paper that never runs out."}, "Papercuts", "A sense of inner peace"], "debt_formula": "1d6+2+Craveability", "passion": "Loves Folding", "special": ["Can create paper cranes that function as surveillance drones."]},
    "65": {"name": "Ex-Celebrity Chef", "description": "You had it all: a hit reality show, a line of designer cookware, and a cookbook that sold millions.
Then came the scandal. Now you're flipping Thickburgers for a pittance, dreaming of the day you can reclaim your former glory, one perfectly seasoned dish at a time.", "skills": {"Charm": 2, "Cooking": 4, "Knife": 2, "Public Speaking": 2}, "gear": ["Chef's Whites (Stained)", "A single, perfect truffle", "A grudge", {"name": "Gourmet Spices", "quantity": 3}], "debt_formula": "2d6+4+Craveability", "passion": "Hates Bad Reviews"},
    "66": {"name": "The Janitor", "description": "You've seen it all.
The blood, the gore, the corporate backstabbing. And you've cleaned it all up.
You are the silent, unseen force that keeps the HyperMall from collapsing under the weight of its own filth.
You know where the bodies are buried because you buried them.", "skills": {"Awareness": 3, "Bash": 2, "Corruption": 1, "Skulk": 3, "Traps": 1}, "gear": [{"name": "Mop", "skill": "Bash"}, "Bucket", "Set of keys to everywhere", "An unnerving smile"], "debt_formula": "1d6+Craveability", "passion": "Hates Messes"}
}
# --- DATA: CONTRACT GENERATION ---
CONTRACT_WHO = {
    "11": {"name": "Protest Leader", "payout_bonus": "1d6", "sg": ["SG1"], "description": "This rabble rouser must be stopped.
A civilized society is based on the principle that we all need to work together, and we can't do that when some sick wastoid fuck is trying to sell our Employees on the notion that they should get bathroom breaks.
Maybe they make subversive art or music, or just go around with slogans and cheap pamphlets.\nWatch out for the disaffected mobs that cling to them like cholesterol.
Might as well put 'em down too while you're at it.", "stats_as": "Civvie"},
    "12": {"name": "Day Shift Manager at The Hamburger Store", "payout_bonus": "1d6", "sg": ["SG1"], "description": "A demigod among wage slaves.\nHamburger Artisans are expected to lay down their lives in defense of Management, so keep that in mind.", "stats_as": "Manager"},
    "13": {"name": "Gang Leader", "payout_bonus": "2d6", "sg": ["SG2", "SG2", "SG3"], "description": "Gangs range from hidebound mafias steeped in tradition to glorified fetish cults run by egomaniacs.
While mostly confined to low income HabPod Blocks, gang activity can happen anywhere.
Corpo Execs regularly hire yakuza-types to rough up the competition and motivate underperforming employees.
The HMPD has connections to all major criminal organizations, to the point that individual precincts are often on opposite sides of armed gang conflicts.
Belonging to a gang is technically a crime, but only if you belong to the wrong gang.\nGang Leaders rule by fear, violence, and Craveability.
They're not just talk - in order to maintain their position, Gang Leaders need to break would-be challengers constantly while making sure the gang remains profitable.
Like any business, gangs exist to make money. Ineffectual leaders are disposed of quick, usually in house, but occasionally by contracted outsiders.", "stats_as": "Gang Leader"},
    "14": {"name": "Military-Grade Cyborg", "payout_bonus": "2d6", "sg": [], "description": "Trained in the arts of war, these cyborgs are extremely dangerous one on one.
Even Gene Warriors have trouble handling them, often relying on superior numbers to take them down.\nExcept for the occasional rich body-mod enthusiast, Military-Grade Cyborgs are all combat veterans.
They'll use superior tactics, dirty tricks, and sacrifice any underlings they have to stay alive.
They'll run the moment they get overwhelmed.\nWhile their cyberware is very illegal, many are exempt from prosecution under the Midlands Act by virtue of their corporate employment.
Regular cops are likely to be too scared to try to arrest a Borg without backup.", "stats_as": "Military-Grade Cyborg"},
    "15": {"name": "Corrupt HyperMall PD Captain", "payout_bonus": "2d6", "sg": ["SG1", "SG3"], "description": "\"Corrupt\" is redundant here.
The HMPD couldn't exist without backroom deals to pay for all their shiny toys: armoured vehicles, state of the art interrogation chambers, and the latest Heavy Weapons.
The Captain is well armed and has the manpower to toss their weight around.\n\"Corrupt\" could also mean \"Refuses Bribes,\" a clear sign of mental illness in police.
Unfortunately, once a cop develops morals, the condition is terminal.
The only solution is to end their suffering as humanely as possible.", "stats_as": ["Gene Warrior", "Grunt Pig"]},
    "16": {"name": "Heterodox Priest of The Consumer", "payout_bonus": "2d6", "sg": ["SG1"], "description": "Their crazed sermons conflict with mainstream theology, which is why they must be killed.
Nip the schism in the bud before their congregation grows.\nPriests are rarely without at least a few loyal Cultists to protect them.", "stats_as": "Consumerist Priest"},
    "21": {"name": "Controversial Livestreamer", "payout_bonus": "1d6", "sg": [], "description": "They spout some truly heinous propaganda and vitriol on their channel.
SWATing just doesn't phase them anymore. It's time to Cancel them once and for all.\nThey could be a 24/7 Truman (viewer donations control every aspect of their life), a raw meat libertarian, an urban survivalist, a lifestyle streamer, an OnlyFeet model, a Gamer, or another Slaughtr™ Contractor who streams their murders.\nWhatever they are, they're scum, and they deserve whatever punishment you dole out.", "stats_as": ["Civvie", "Gun Nut"]},
    "22": {"name": "Rampaging Angel", "payout_bonus": "3d6", "sg": [], "description": "You've been called in to kill a monster.
Try not to die horribly.\nAngels shape their bodies from corpses and just keep coming back as long as there's enough tissue around.
Clean up after yourself!", "stats_as": "Angel"},
    "23": {"name": "Psychotic Biotech CEO", "payout_bonus": "5d6", "sg": ["SG5"], "description": "They sought a kind of capitalist perfection: the body as a tool for the acquisition of Wealth.
Unfortunately, they've been driven mad and no longer recognize the world around them.
For complicated legal reasons, this CEO can't be ousted from their position for any reason and must be removed in a more literal manner.", "stats_as": "CEO", "special": "+3 x Random Mutations"},
    "24": {"name": "Powerful Executive", "payout_bonus": "4d6", "sg": ["SG4"], "description": "Executives are inevitably surrounded by hangers-on, sycophants, and bootlickers.
They have the protection of their corporate masters and should not be trifled with, if, quote, \"you ever want to work in this town again.\"", "stats_as": "Executive"},
    "25": {"name": "Rogue AI", "payout_bonus": "4d6", "sg": ["SG1"], "description": "By the time the Contractors show up, a hostile AI will have taken control of its location and is likely to have killed every human it could.
The extent of its control depends on what it was capable of before going rogue.
A SmartToilet AI could conceivably lock someone in a bathroom and flood it with sewage, for example, but is unlikely to be able to leave the HabPod it was assigned to.", "stats_as": "AI"},
    "26": {"name": "Low Level Retail Employee", "payout_bonus": "1d6", "sg": [], "description": "Just some rando, your basic cashier or warehouse worker.
Their coworkers might take issue with you turning this poor shlub into ground meat, but what are they gonna do about it?
Cry?", "stats_as": "Civvie"},
    "31": {"name": "Baba Yaga Pilot", "payout_bonus": "3d6", "sg": ["SG1"], "description": "If you can get them out of their walking war crimes, they shouldn't be any harder to kill than your average soldier.
Don't try to take a Baba Yaga head on; there won't be enough of you left for a positive ID.", "stats_as": "Baba Yaga Pilot"},
    "32": {"name": "Extrasolarian Tourist", "payout_bonus": "2d6", "sg": [], "description": "They're on \"vacation,\" a concept as alien to you as their biology.
They splorp, ooze, or tumble over everything, fascinated by the quaintness of human civilization.
Show them some HyperMall hospitality.", "stats_as": "Extrasolarian", "special": "2 Random Mutations, 1 Random Psionic Ability"},
    "33": {"name": "Gene Warrior", "payout_bonus": "1d6", "sg": ["SG1"], "description": "GMO foot soldiers owned by the ACF and other corps, designed to be faster, stronger, and more obedient than baseline humanity.
They're much smarter than Grunt Pigs, but that isn't saying much.
Expect a hard fight.\nThey will almost always call for backup.", "stats_as": "Gene Warrior"},
    "34": {"name": "Vapid Celebrity", "payout_bonus": "1d6", "sg": [], "description": "The emptiness of social media and stimulant abuse has left them a cicada husk of a person.
They create nothing. They do nothing. The personalities, opinions, and desires of those around them scuttle, crab-like, into their empty cranium.
They are beautiful and hideous and paper thin.", "stats_as": "Civvie"},
    "35": {"name": "Contractor Legend", "payout_bonus": "6d6", "sg": ["SG1"], "description": "Maybe the Contractors met them at last year's Contractor Ball, or they've heard stories of their exploits in hushed tones in shady bars.
Maybe they even worked together once. This Contractor is famous, a one of a kind badass with dozens of jobs under their belt.
They say there's no one they can't kill. Prove you're better.", "stats_as": "Contractor Legend", "special": "Roll their Background as normal.", "MT": 36, "ST": 12, "DT": 40, "damage": "4d6+6 (Any Weapon)"},
    "36": {"name": "Thought Terrorist", "payout_bonus": "3d6", "sg": ["SG1"], "description": "The most dangerous kind of criminal is one whose crimes are theoretical.
Don't listen to what they have to say or you might succumb to Communist infohazards. Burn any literature you find.
Do NOT open any mail they send you.", "stats_as": ["Gun Nut", "Cultist", "Economite Operative"]},
    "41": {"name": "Pillar of the Community", "payout_bonus": "2d6", "sg": [], "description": "The Target is someone everyone looks up to.
They're a genuinely good person that has improved the lives of those around them.
No one can say the same about you.\nPeople come to them for advice, help in hard times, and good conversation.
The Contractors are going to snuff them out.", "stats_as": "Civvie"},
    "42": {"name": "Smuggler of Illicit Content", "payout_bonus": "2d6", "sg": ["SG2"], "description": "Anyone willing to go up against the Border Expansion and Aerospace Security Task-force (BEAST) must be nuts.
BEAST doesn't fuck around; they'll zap a refugee Starship full of war orphans out of LEO for having outdated credentials.
Fail a surprise inspection and BEAST will confiscate your ship and torture you until you confess.
Nasty fuckers.\nSmugglers shoot first and don't ask questions. Their life, their reputation, and their money's on the line.
They don't have time to waste on normies.", "stats_as": ["Shoplifter", "Gun Nut"]},
    "43": {"name": "Serial Killer", "payout_bonus": "2d6", "sg": [], "special": "Elusive", "description": "What kind of monster kills for free?
Mercwork makes sense - you off someone because somebody told you to. That's fine. But to do it just because?
Can't wrap my head around it.\nSerial Killers are a rare breed.
They seek the thrill of the hunt, the perverse pleasure of the kill, and the feeling of control that murder gives them.
They're all pathetic losers, basically. The fact that their victims come back postmortem forces the would-be Dahmers of the HyperMall to be extremely cautious with their identities.
Or it forces them to hunt only society's most vulnerable, which is even more pathetic.\nEvery Serial Killer has a specific murder technique or calling card they're known for, giving them nicknames like The Night Surgeon, Johnny Reaper, The Penis Stealer, The Butcher of Embassy Row, The Wonderful World of Wisconsin Strangler, or Murder Guy.", "stats_as": ["Civvie", "Grunt Pig", "Executive", "CEO"]},
    "44": {"name": "NANCY Pilot", "payout_bonus": "2d6", "sg": ["SG1"], "description": "The quick skirmishers and scouts of the exomech family, NANCYs are fast and deadly, able to mount Heavy Weapons on their shoulder hardpoints while simultaneously wielding a variety 
of handheld gear. Experts opt for carbide lances and purpose-built jumbo katanas to duel with other pilots (it's a kind of foreplay).
All this, and they're still fast as hell.\nThe direct spinal nanoplug allows pilots to \"feel\" their NANCY, experiencing every piston and hydraulic as if it were their own flesh and blood.
Vets grow extremely attached to their rigs, often becoming agitated when forced to exit their cockpits for the monthly hose down.
Many report a kind of dysphoria when disconnected from their NANCY, experiencing discomfort at the fact that they don't have shoulder-mounted cluster rockets or digitigrade legs.
Not that their employers care; they just use this as an excuse to force their pilots to take unpaid overtime.", "stats_as": "NANCY Pilot"},
    "45": {"name": "Your Handler's Estranged Spouse", "payout_bonus": "2d6", "sg": [], "description": "\"They took my wife in the divorce,\" is a common refrain among Handlers.
To everyone's surprise, the psychopaths responsible for arranging paid murder are rarely able to maintain stable interpersonal relationships. Their solution?
Arranged murder.", "stats_as": "Civvie"},
    "46": {"name": "The Invisible Gorilla King", "payout_bonus": "6d6", "sg": ["SG1", "SG2"], "description": "He's invisible and highly intelligent, not to mention strong as hell.
Every other operative we've sent to take him out has wound up with a coconut where their head should be.", "stats_as": "The Invisible Gorilla King"},
    "51": {"name": "The Gender Construct", "payout_bonus": "6d6+6", "sg": [], "description": "Too bloated and immense to fully perceive, The Gender Construct is humanity's greatest hubris.
Top 10, at least. Gender nonconforming Contractors are advised to take extreme caution, as The Gender Construct psionically enforces rigid hierarchies and binaries in its immediate area.
Mindless, writhing, hateful, The Gender Construct denies its victims the dignity of choice.", "stats_as": "The Gender Construct"},
    "52": {"name": "Posthuman Warlord", "payout_bonus": "4d6", "sg": ["SG1", "SG3"], "description": "All you need to establish a micronation is enough firepower to make sure nobody fucks with you.
The Posthuman Warlord has guns in spades and is crazy enough to use them on anyone that gets too close.
They lead a band of car-obsessed social dregs and bloodthirsty mutants, operating out of the squatted ruins of corporate civilization, preying on the weak, the meek, and the stupid.\nNames: Morghast, Woundlick, Angry Andy, The Gun Eater, Virginator, Doomrunner, Lord Gloom, Thraangak the Skull Taker, Azakar, Ruin, Dirge Queen", "stats_as": ["Executive", "Gun Nut", "Gene Warrior", "CEO"], "special": "+3 Random Mutations"},
    "53": {"name": "Porcupine Man, Illegal Vigilante", "payout_bonus": "3d6", "sg": [], "description": "An anonymous CEO turned vigilante, Porcupine Man stalks the dirty halls and maintenance corridors of the HyperMall meting out Justice to ne'er-do-wells and loiterers at the end 
of a sharp quill. Out of the shadows emerges the Needle of Vengeance, Porcupine Man!", "stats_as": "Porcupine Man", "MT": 30, "ST": 10, "DT": 100, "damage": "3d6 Damage (Gunkata) / 1d3 Meat Damage (automatically dealt to foes in melee)"},
    "54": {"name": "Master Hacker", "payout_bonus": "4d6", "sg": ["SG1"], "special": "Elusive", "description": "How're you gonna find someone behind seven proxies?
They'll burn you the second you come for them. They'll empty your accounts in minutes, load your FleshHub with illegal content and drop an anon tip to HMPD if you so much as breathe in their direction.
They'll make your shower sentient and order it to kill you. You think running the Net is kiddie shit?
Do not fuck with Hackers.", "stats_as": "Grey Hat", "damage": "+1d6 Damage"},
    "55": {"name": "Freshvalue Deals, Toronto Mariners Starting Pitcher", "payout_bonus": "2d6", "sg": ["SG1"], "description": "One of the ICL's best pitchers, Deals is most famous for his 237 mph blastball that took Gonzo Oort Jr.'s leg clean off on a hit-by-pitch.
8'9\", 500kg, and wanted for millions in unpaid child support. He pitched an immaculate inning against the Fightin' Irish while clinically dead.", "stats_as": "Military-Grade Cyborg", "special": "without the cyberware. Mutations: All-Star Elbow, Myostatin Inhibitor, BioZoom Ocular Enhancer"},
    "56": {"name": "Dr. Acula, Billionaire Playboy & Rumoured Immortal", "payout_bonus": "4d6", "sg": ["SG2"], "description": "\"This shit ain't nothing to me, man.\" You know who this is. He drinks blood, hates sunlight, and can't cross running water. His lifestyle brand is extremely profitable.\nBecause the HyperMall is one big building, Dr. Acula doesn't need permission to enter stores or HabPods. He avoids 
Consumerist churches out of habit and burns on contact with Holy Symbols.", "stats_as": "CEO", "special": "plus the following:\nMutations: Rapid Infusion Process, Van der Waals Pads, Pit Organs\nPsionics: Phasing, Commanding Voice, Accelerate Decay, Corpse Command"},
    "61": {"name": "ThePaganBaller, Far-Right Ideologue and Supplement Guru", "payout_bonus": "3d6", "sg": ["SG2"], "description": "Despite publicly admitting to running a human trafficking operation multiple times, ThePaganBaller remains MallNet's most popular and profitable misoginfluencer.
His audience consists of alienated male youth and the terminally unfuckable.
He is a vocal adherent to the ancient caucasian practice of eating uncooked meat and buying testosterone cream, traditions he claims are how he's able to afford his many exotic cars.
He offers courses on pick up artistry, investing, and phrenology.\nHe carries a Kill Falcon, but doesn't know how to use it.
His abs are cosmetic implants.", "stats_as": "Civvie"},
    "62": {"name": "Croaking Abbot of Our Lady of the Spawning Pool Amphibious Rectory", "payout_bonus": "3d6", "sg": ["SG1", "SG2"], "description": "More amphibian than man, the Croaking Abbot reads the word of the Frog Father to the faithful, as much a teacher as a war-ready crusader.
The Children of the Frog will kill any infidel that defiles their sacred, swampy sanctum.\nThe GM can decide to include the Amphibious Rectory as part of the Contract Location if they think it will be more interesting.", "stats_as": "Child of the Frog", "MT": 25, "ST": 12, "DT": 30, "armor": 3, "damage": "3d6 Damage (Funny Bone)"},
    "63": {"name": "Mad Scientist", "payout_bonus": "3d6", "sg": ["SG1"], "description": "No one knows what the Mad Scientist might be cooking up.
It could be a virus that turns people into horses, a Time Gun that shoots your dad in the balls seconds before conception, or a bomb that only kills left-handed people.
Whatever it is, it's really dangerous and probably worth a lot of money.", "stats_as": "Manager", "special": "plus whatever Science moves you want to give them"},
    "64": {"name": "Archangel, Harbinger of Death", "payout_bonus": "6d6+6", "sg": [], "description": "Indescribably dangerous.
You'll be lucky if there's enough of you left to shove into a bodybag.
Bring the biggest, nastiest guns you have and pray to The Consumer you make it back alive.\nSome advice: if you can get someone else (HMPD, BEAST, UCLF) to engage the Archangel, you might have a chance.
"sg": ["SG2"]},
    "12": {"name": "Le Long Cochon", "payout_bonus": "3d6", "sg": ["SG1", "SG2"]},
    "13": {"name": "UCLF Mech Base", "payout_bonus": "3d6", "sg": ["SG1", "SG3", "SG4"]},
    "14": {"name": "The Food Court", "payout_bonus": "1d6", "sg": ["SG1"]},
    "15": {"name": "The Monorail", "payout_bonus": "1d6", "sg": ["SG1"]},
    "16": {"name": "Succulent Flesh of the Divine Graveyard & Mini Golf Course", "payout_bonus": "1d6", "sg": ["SG3"]},
    "21": {"name": "Grand Basilica of The Consumer Brought To You By Taco House", "payout_bonus": "3d6", "sg": ["SG1", "SG2", "SG3"]},
    "22": {"name": "Private Villa 
at the Epstein Valley Resort", "payout_bonus": "3d6", "sg": ["SG1", "SG3", "SG4"]},
    "23": {"name": "Bunker with AI Guardian", "payout_bonus": "2d6", "sg": ["SG1", "SG1", "SG2", "SG3"]},
    "24": {"name": "Top Floor Boardroom", "payout_bonus": "3d6", "sg": ["SG1", "SG3"]},
    "25": {"name": "Some Shithole Bar or Back Alley", "payout_bonus": "1d6", "sg": ["SG1"]},
    "26": {"name": "The Sewers", "payout_bonus": "1d6", "sg": ["SG1"]},
    "31": {"name": "His Majesty’s Royal Lunar Embassy", "payout_bonus": "3d6", "sg": ["SG1", "SG2", "SG3"]},
    "32": {"name": "The Vine-Choked Depths of Ape Town, Domain of the Gorilla King", "payout_bonus": "1d6", 
"sg": ["SG2"]},
    "33": {"name": "Haunted Goth Clothing Store", "payout_bonus": "1d6", "sg": ["SG1"]},
    "34": {"name": "AAA Gaming Convention", "payout_bonus": "1d6", "sg": ["SG1"]},
    "35": {"name": "The Anglo-infested Catacombs Beneath the HyperMall", "payout_bonus": "1d6", "sg": ["SG3"]},
    "36": {"name": "John Q. HyperMall Ultra War Memorial Obelisk & Adult SplashZone", "payout_bonus": "1d6", "sg": ["SG1"]},
    "41": {"name": "Corporate Office", "payout_bonus": "2d6", "sg": ["SG1"]},
    "42": {"name": "Penthouse", "payout_bonus": "2d6", "sg": ["SG1"]},
    "43": {"name": "Wonderful World of Wisconsin Amusement Park", "payout_bonus": "1d6", "sg": ["SG1"]},
    
"44": {"name": "MegaMaxx Incarceration Pit", "payout_bonus": "6d6+6", "sg": ["SG6"]},
    "45": {"name": "Steamboat Willie's No Loads Refused Wet N Wild Sewer Tour", "payout_bonus": "2d6", "sg": ["SG1"]},
    "46": {"name": "HyperMall PD Precinct", "payout_bonus": "3d6", "sg": ["SG1", "SG1", "SG2", "SG3"]},
    "51": {"name": "Midlands Cigarettes KillDome", "payout_bonus": "1d6", "sg": ["SG4"]},
    "52": {"name": "Secret Research Facility", "payout_bonus": "3d6", "sg": ["SG3", "SG4"]},
    "53": {"name": "The Cosmic Abattoir", "payout_bonus": "2d6", "sg": ["SG2"]},
    "54": {"name": "DynaCore Boreal Adventures BioDome Resort", "payout_bonus": "3d6", "sg": ["SG1", "SG2"]},
    "55": {"name": 
"The Mystic Uqbar Hotel & Casino", "payout_bonus": "2d6", "sg": ["SG1", "SG2", "SG3"]},
    "56": {"name": "Path of Awakening Organic Homeopathic Kundalini Birth Clinic", "payout_bonus": "1d6", "sg": ["SG1"]},
    "61": {"name": "Blast 'Em Up Firearm Depot & Live Fire Shooting Range", "payout_bonus": "1d6", "sg": ["SG2", "SG3"]},
    "62": {"name": "The Paintorium", "payout_bonus": "2d6", "sg": ["SG1"]},
    "63": {"name": "Night Club", "payout_bonus": "3d6", "sg": ["SG1"]},
    "64": {"name": "Secret Society HQ", "payout_bonus": "6d6+6", "sg": ["SG1", "SG6"]},
    "65": {"name": "Theatre 16 Sponsored by SmartMeat Innovations", "payout_bonus": "2d6", "sg": ["SG1", "SG2"]},
 
   "66": {"name": "The Death Dimension", "payout_bonus": "6d6+6", "sg": []}
}

CONTRACT_HOW = {
    "11": {"name": "Drive By", "payout_bonus": "3d6"},
    "12": {"name": "Financial Assassination", "payout_bonus": "2d6"},
    "13": {"name": "Targeted Trauma", "payout_bonus": "2d6"},
    "14": {"name": "Explosive Action", "payout_bonus": "1d6"},
    "15": {"name": "False Flag Attack", "payout_bonus": "1d6"},
    "16": {"name": "Honourable Combat", "payout_bonus": "2d6"},
    "21": {"name": "Let Me Axe You A Question", "payout_bonus": "2d6", "special": "Bonus +2d6 Payout if you use no other weapon during the course of the Contract."},
   
 "22": {"name": "Martial Humiliation", "payout_bonus": "2d6"},
    "23": {"name": "Does This Taste Funny To You?", "payout_bonus": "1d6"},
    "24": {"name": "Beast Mode", "payout_bonus": "1d6"},
    "25": {"name": "Concrete Shoes", "payout_bonus": "2d6"},
    "26": {"name": "Tear Out The Cancer Of Innocence With Your Bloody Teeth", "payout_bonus": "1", "special": "Gain +1 Payout for every bystander permakilled."},
    "31": {"name": "Abduction", "payout_bonus": "2d6"},
    "32": {"name": "Dragging Hector's Corpse", "payout_bonus": "2d6"},
    "33": {"name": "Preemptive Patricide", "payout_bonus": "1d6"},
    "34": {"name": "No Permakilling", "payout_bonus": "1d6"},
  
  "35": {"name": "S-Rank Stealth", "payout_bonus": "4d6"},
    "36": {"name": "Rescue", "payout_bonus": "2d6"},
    "41": {"name": "Naked and Afraid", "payout_bonus": "4d6"},
    "42": {"name": "I'll Have You Know I Graduated Top Of My Class", "payout_bonus": "2d6"},
    "43": {"name": "Right Between the Eyes", "payout_bonus": "3d6"},
    "44": {"name": "Advanced Interrogation", "payout_bonus": "3d6"},
    "45": {"name": "Manchurian Candidate", "payout_bonus": "3d6"},
    "46": {"name": "Love Can't Bloom", "payout_bonus": "1d6"},
    "51": {"name": "Lethal Attraction", "payout_bonus": "4d6"},
    "52": {"name": "On Stream", "payout_bonus": "1d6"},
 
   "53": {"name": "RSVP", "payout_bonus": "3d6", "sg": ["SG3"]},
    "54": {"name": "Gom Jabbar", "payout_bonus": "2d6"},
    "55": {"name": "The Gunslinger", "payout_bonus": "2d6", "special": "Bonus +2d6 Payout if you use no other weapon during the Contract."},
    "56": {"name": "Knife To Meet You", "payout_bonus": "2d6", "special": "Bonus +2d6 Payout if you use no other weapon during the Contract."},
    "61": {"name": "Sword is the Word", "payout_bonus": "2d6", "special": "Bonus +2d6 Payout if you use no other weapon during the Contract."},
    "62": {"name": "Accident", "payout_bonus": "4d6"},
    
"63": {"name": "Radical!", "payout_bonus": "4d6"},
    "64": {"name": "The Best Day Ever", "payout_bonus": "6d6"},
    "65": {"name": "Pizza Time", "payout_bonus": "2d6"},
    "66": {"name": "Hope Eradicated", "payout_bonus": "6d6+6"}
}

CONTRACT_WHY = {
    "11": "None of your business", "12": "None of your business", "13": "None of your business", "14": "None of your business", "15": "None of your business", "16": "None of your business",
    "21": "The Target chews with their mouth open", "22": "Creative dispute", "23": "The Target snitched", "24": "Insurance fraud", "25": "This is the only way the Client can climax", 
"26": "The Target was talking shit",
    "31": "The Target leaked the Client's private information and / or nudes", "32": "Suicide: the Client IS the Target", "33": "The Client thinks it would be funny", "34": "The Target turned their back on The Crustaceal Path", "35": "The Pig God demands a sacrifice", "36": "The Target was a bully growing up",
    "41": "It's strictly business", "42": "The Target has incriminating evidence that could ruin the Client", "43": "Divorce", "44": "The Target personally slighted the Client", "45": "The Target killed or had sex with the Client's mom, dad, 
or both", "46": "It’s part of a prophecy",
    "51": "The Target is a real piece of shit", "52": "The Client is a real piece of shit", "53": "The Target is a known Liberal", "54": "This is all part of an ancient shadow war between secret societies", "55": "The Target backed out of an important deal", "56": "Killing the Target will tank some stocks, making the Client (and you, if you're smart) rich",
    "61": "The Target stole something from the Client", "62": "The Target had it coming", "63": "The Target knows something they shouldn't", "64": 
"Blood feud", "65": "The Target expressed anti-patriotic beliefs", "66": "Ask again and I'll kill you"
}

CONTRACT_KNOW = {
    "11": {"name": "Not Very Effective", "payout_bonus": "2d6", "description": "The Target is totally immune to a common form of damage (bullets, blades, Stress, fire, etc.)"},
    "12": {"name": "Gangster's Paradise", "payout_bonus": "1d6", "description": "The Target's Location is known gang territory.
Roll on the Ganger Background to find out which gang controls the turf.
They won't take too kindly to heavily armed outsiders poking around and shooting up the place."},
    "13": {"name": "Posthuman Excellence", "payout_bonus": "1d6", "description": "The Target or one of their goons is heavily mutated (+3 Random Mutations)."},
    "14": {"name": "Psychic Patrol", "payout_bonus": "1d6", "description": "The Target or one of their goons is a powerful Psionic (+3 Random Psionic Abilities)."},
    "15": {"name": "Harder Better Faster Stronger", "payout_bonus": "1d6", "description": "The Target is a fierce combatant, dealing +1d6 damage."},
    "16": {"name": "Diplomatic Immunity", "payout_bonus": "2d6", "description": "The Target is some kind 
of corporate diplomat or CROSSPOL cop, and thus enjoys protection from prosecution for any crimes they commit.
They can get away with a ton of truly heinous shit without repercussion.
Killing them is likely to have consequences."},
    "21": {"name": "Get in the Robot", "payout_bonus": "1d6", "description": "The Target drives an exomech.
If they already have an exomech, one of their goons has one as well."},
    "22": {"name": "Fame", "payout_bonus": "1d6", "sg": ["SG1"], "description": "The Target is famous or infamous.
Fans and / or haters swarm the Target at all times."},
    "23": {"name": "Acquaintance", "payout_bonus": "1d6", "description": "The Target knows one of the Contractors personally.
They may be friends, colleagues, distant relatives, neighbours, or rivals.
The Target would be able to pick that particular contractor out of a crowd with ease, and vice versa."},
    "24": {"name": "Really Tough", "payout_bonus": "1d6", "description": "The Target has +6 to all Thresholds and +3 Armour to all Hit Locations."},
    "25": {"name": "Retribution", "payout_bonus": "1d6", "description": "The Target's associates, family, or gang will stop at nothing to get revenge once they're dead.
That sounds like a problem for Future You."},
    "26": {"name": "Flight Logs", "payout_bonus": "1d6", "description": "The Target is involved in some extremely shady shit.
Maybe they're a member of a secret society, part of a mutant trafficking ring, a serial killer, or a straight up war criminal.
None of the above crimes are actually illegal if the victims are poor enough.
The true extent of their immorality will only be revealed through clever investigation and advanced interrogation."},
    "31": {"name": "Blackmail", "payout_bonus": "1d6", "description": "The Target has dirt on one or more of the Contractors or information that is personally relevant to them.
The Target will almost certainly use this to manipulate the Contractors."},
    "32": {"name": "Bling", "payout_bonus": "0", "description": "The Target has a very cool custom gun.
If they can't use guns, then they have something of similar value that is equally cool."},
    "33": {"name": "Hot Stuff", "payout_bonus": "1d6", "description": "The Target is dangerously attractive.
They can and will use their looks to manipulate the Contractors and everyone around them."},
    "34": {"name": "Unprofessional Behaviour", "payout_bonus": "1d6", "description": "There's another team of Contractors trying to steal your kill.
Dick move, guys."},
    "35": {"name": "I'm the Jinxer, Baby", "payout_bonus": "1d6", "description": "The Target is a member of the Misfortunates or protected by one.
They seek only to spread chaos and laughter through violent pranks, annoying riddles, and incessant japes.
They have it coming."},
    "36": {"name": "The Element of Un-Surprise", "payout_bonus": "1d6", "description": "The Target knows it's coming and has prepared appropriately."},
    "41": {"name": "Ongoing 24 Hour Depopulation Event", "payout_bonus": "1d6", "description": "The People voted and chose your Target’s sector for the monthly purge.
There's bloodcrazed cops, looters, and corpses everywhere. The tiled hallways of the HyperMall are stained with blood.
The Resurrection Matrix is disabled for all non-cops with Debt Threshold <25, which may or may not include the Target."},
    "42": {"name": "No Money, Mo Problems", "payout_bonus": "0", "sg": ["SG1"], "description": "The Target is completely broke or just lost their fortune gambling on the Central Blockchain.
The loan sharks after the Target don't want you interfering, since they can't collect if the Target's dead.
Expect extra resistance."},
    "43": {"name": "Hostage Party", "payout_bonus": "2d6", "description": "The Target and their goons have taken 1d6+1 hostages and have at least 2 Permadeath Cubes they'll use if their demands aren't met.
So far the HyperMall PD has locked down the immediate area and fined one of the hostages for loitering.
They're here to collect overtime pay.\nThe hostages are liable to get in your way or attempt to infect you with Stockholm Syndrome, so watch out.
You don't have to rescue them if you don't want to."},
    "44": {"name": "Secondary Objective: Theft", "payout_bonus": "1d6", "description": "In addition to whatever else you have to do, the Client wants you to steal something important or valuable from the Target.
Go get it."},
    "45": {"name": "Multiple Targets", "payout_bonus": "1d6", "description": "Oh boy, more work!
Roll 1d3 additional Targets in the same general Location. You gotta take them all out."},
    "46": {"name": "Zombie Outbreak", "payout_bonus": "1d6", "description": "There are Zombies and panicked Civvies everywhere throughout the Target's sector.
Chaos reigns. You have 2d6 hours before every exit is locked down.
Don't get bit."},
    "51": {"name": "Death Storm", "payout_bonus": "3d6", "description": "The Death Dimension shudders, smashing through the Resurrection Matrix and disrupting the fabric of the Meat World.
The Resurrection Matrix in the Target's sector is down, meaning you can be permanently killed.
Angels and other Death Entities flock to the Death Storm, eager to punish mortals."},
    "52": {"name": "Huge Sale", "payout_bonus": "1d6", "description": "A store very close to the Target's location swarms with deal-hungry Civvies.
Things are bound to turn violent sooner rather than later.
A random piece of Gear is 90% off, assuming you can pry one out of the hands of a Shopper ready to die for the deal."},
    "53": {"name": "Ape Incursion", "payout_bonus": "2d6", "description": "Invisible Gorillas have launched an assault nearby, drawing in crowds of curious onlookers.
There's not much to see besides cops getting tossed around by invisible primates, but it's a real hoot nonetheless."},
    "54": {"name": "Major Seasonal Holiday", "payout_bonus": "1d6", "description": "It's Christmas.
Everyone is hunkered in their HabPods, nervously waiting for the Holiday Demon to try to take their presents.
Saint Krampus hunts the night for flesh. You will not receive holiday pay or time off."},
    "55": {"name": "Fragmented Soul", "payout_bonus": "3d6", "description": "The Target has split their essence across 1d3+1 Locations.
Upon being killed, they will resurrect at a CHRIST in one of these other Locations and will continue to do so until you recover all the pieces of their soul.
These soul fragments take the form of throbbing crystals, childhood toys, living soul slaves, or expensive watches."},
    "56": {"name": "Secondary Objective: Frame Job", "payout_bonus": "1d6", "description": "In addition to whatever else you have to do, you need to plant incriminating evidence or illegal content on the Target or their harddrive without getting caught."},
    "61": {"name": "YOU ARE A MEAT MACHINE HALLUCINATING CONSCIOUSNESS", "payout_bonus": "3d6", "description": "The Doors Within remain closed.
Die and return. Open the Emerald Way. Witness what remains hidden to the Third Eye.
Die as One and destroy the Universe, Become All. Shed the skin of Self.\nYou won't be able to find or kill the Target without taking a whole bunch of drugs.
Don't ask why. Just hit this vape.\nThe Contractors are going on a psychedelic adventure.
Embrace the weird."},
    "62": {"name": "KILL SIX BILLION CORPO COPS", "payout_bonus": "6d6+6", "description": "Somebody ratted you out.
The Pigs are going to kill you, motherfucker, and there's nothing you can do about it unless you kill them first.\nYou have about 2 minutes before they kick down your door and put a bullet through your cranium.
They won't stop chasing you. You NEED to finish this Contract to clear your name.
Make it happen."},
    "63": {"name": "ARTIFICIAL DEATH IN THE WEST", "payout_bonus": "6d6", "description": "Somebody left the oven on and caused the shard of the Torment Algorithm in charge of the Target's sector to suffer mass brain death.
MallNet access is impossible from within the sector; water, electricity, atmospherics, and porn are inaccessible. This is an apocalyptic scenario.
All communication systems are down, and the HyperMall PD is in complete disarray.
The Resurrection Matrix is functional, but because MallNet is down, the CHRIST souldata cloud is overwhelmed and can't process requests properly.\nPeople are locked in their HabPods or stuck outside.
You can't buy anything, doors won't open, and the air is slowly becoming unbreathable.
Even places abandoned by the ACF like Ape Town and the Catacombs have rudimentary AI infrastructure to keep atmospherics running (if for no other reason than they forgot to turn it off).
You have a very limited amount of time before the whole sector is declared terra non grata.
Your best bet might be to extract the Target and kill them elsewhere to ensure they never resurrect."},
    "64": {"name": "ET TU, BRUTE?", "payout_bonus": "6d6", "sg": ["SG2"], "description": "Each Contractor's best friend or favourite relative has been hired as security by the Target.
You can kill them, but friends are really hard to come by, and they probably won't enjoy being shot.
Go around the table and ask each Contractor for their best friend's name and something unique about them."},
    "65": {"name": "HYPERMALL MUST DIE", "payout_bonus": "6d6+6", "description": "Your Handler warned you: This Target has an Automatic Counter-Kill attached to their genetic profile.
You sign up and it'll go live.\nAs soon as your e-sig touches the Contract, everyone's FleshHub will light up.
Public PSA: Your names and faces, known Mutations, Psionics, and equipment. Cash prize.
100 Debt per Head, payable upon proof of permadeath or live capture.\nEvery desperate Gun Nut, wage slave, cuck, Civvie, and Grunt Pig is out for blood.
Every single person you encounter is a potential combatant. You can't trust anyone and you can't hide.
You've got a job to do. Just getting to your Target is going to be a Herculean task."},
    "66": {"name": "UNLIMITED VIOLENCE", "payout_bonus": "6d6+6", "description": "Roll on this table six times.
Huge profit potential. Get creative. Make it work."}
}

CONTRACT_DONT_KNOW = {
    "11": {"name": "Attack of the Clones", "payout_bonus": "1d6", "description": "The Target is a secret clone of one of the Contractors or vice versa."},
    "12": {"name": "I've Got A Bad Feeling About This", "payout_bonus": "2d6", "description": "The Target set up an ambush at the Location and the Contractors are about to walk right in. Give them a hint or two that something's not right before they get their dicks handed to them."},
    "13": {"name": "The Handler is Going to Betray Them", "payout_bonus": 
"2d6", "description": "They might keep the payout, snitch to the cops, or send in another team to mop up the Contractors once the job is done.
You should probably get revenge."},
    "14": {"name": "Well Armed", "payout_bonus": "1d6", "description": "The Target or their goons have way better Gear than the Handler let on.
They might have Heavy Weapons, stronger body armour, exomechs, or additional security tech."},
    "15": {"name": "Bad Intel", "payout_bonus": "0", "description": "Reroll who they're killing in secret but don't change the Payout."},
    "16": {"name": "Body Double", "payout_bonus": "0", "description": "The Contractors are going after a surgically-altered body double that looks like the Target.
They won't get a Payout without a positive genome match.
Roll the real Target’s Location separately."},
    "21": {"name": "This Is All an Elaborate TV Show", "payout_bonus": "1d6", "description": "They're being filmed by a disguised camera crew.
Once they kill the Target, the host will walk out and reveal everything.
Depending on their job performance, the Contractors might win bonuses or suffer penalties."},
    "22": {"name": "The Target is a Corporate Spy", "payout_bonus": "0", "description": "The Target has valuable or dangerous intel on their person.
It could be blackmail, product information, sales figures, nudes, whatever.
It's not part of the Contract to recover the intel, but it's probably worth something.
The Target's employer and / or the company they stole from want that intel back, and they'll probably kill for it."},
    "23": {"name": "The Target Is A Robot", "payout_bonus": "0", "description": "They think they're a person.
They might be a delusional piece of machinery, or they could look and talk exactly like a person.
Only way to know for sure is to kill them."},
    "24": {"name": "This Is All a Test", "payout_bonus": "2d6", "sg": ["SG4"], "description": "The Target set everything up just to judge the Contractor's abilities and has the receipts to prove it.
They have an even more dangerous and lucrative Contract they want completed, assuming the Contractors survive.
They'll say things like \"most impressive\" while emerging from the shadows.\nIf they take the job, it gains +3d6 Payout and SG6."},
    "25": {"name": "The Target is Already Dead", "payout_bonus": "0", "description": "Oooh, how mysterious.
Maybe another team got there first, or maybe it's a ruse.
Maybe the Contractors walk in the moment the Target drops dead.
Use this option to build intrigue."},
    "26": {"name": "Elusive", "payout_bonus": "1d6", "description": "At the Location, the Contractors find clues to the Target's whereabouts rather than the actual Target.
They're going to have to put in some legwork to figure out where the Target actually is and catch them.
Serial Killers and Master Hackers are automatically Elusive."},
    "31": {"name": "Going Out With A Bang", "payout_bonus": "0", "description": "The Target has a bomb in their chest.
It's rigged to blow when their heart stops, dealing 6d6+6 Meat Damage to everything in Long Range.
Brutal."},
    "32": {"name": "Surprise!", "payout_bonus": "3d6", "description": "Roll again on the What Do We Know? table.
They don't get any extra cash, no matter what you roll.\nReroll if you get 66 UNLIMITED VIOLENCE, unless you're a complete sadist."},
    "33": {"name": "The Client Isn't Gonna Pay", "payout_bonus": "0", "description": "Once the job is done, nobody's account balance changes.
Your Handler took a Pay On Delivery Contract, like an idiot. Rookie mistake.
If you want your cash, you're going to need to find the Client."},
    "34": {"name": "The Target Was A Slaughtr™ Executive", "payout_bonus": "0", "description": "There's been a terrible mistake.
The Contractors just killed someone they really shouldn't have: their boss's boss.
If this gets out, the Contractors can expect to be hunted down, or worse, unemployed.
Was it all a big misunderstanding, or is something more nefarious going on? Who set them up?
Why won't the Handler pick up the phone?\nGMs, give Contractors a chance to figure this out before they jeopardize their employment.
Or don't."},
    "35": {"name": "Sting Operation", "payout_bonus": "0", "sg": ["SG1"], "description": "The Pigs set the Contractors up.
The Target? Fake. The Location? Full of plainclothes officers just waiting to jump out and arrest everybody.
There's a 50-50 chance the Handler was in on it (up to the GM). Don't spring the trap right away.
Let the tension build.\nSecurity at the Location is under the control of the police.\nUndercover cops aren't necessarily good actors, and if they're Grunt Pigs pretending to be Civvies, their porcine biology should be a dead giveaway."},
    "36": {"name": "Defenses?
Don't Worry About It", "payout_bonus": "1d6", "description": "The Contractors are in the dark about what kind of protection the Target has.
They can make educated guesses, but the Handler gives them nothing to work with."},
    "41": {"name": "Open Season", "payout_bonus": "0", "description": "Someone put out a Slaughtr™ bounty on one of the Contractors equal to their Debt Threshold.
This is not the Handler's problem."},
    "42": {"name": "The Evil and Corrupt Mainstream Media", "payout_bonus": "1d6", "description": "The Target is a journalist.
They possess evidence that will expose the illicit activities of a prominent CEO or member of the Board.
They just want to do the right thing."},
    "43": {"name": "Assassin Killer", "payout_bonus": "3d6", "description": "The Target is a trained killer or expert martial artist.
Every other team that's been sent to put them down has been perma'd. The Handler mentioned none of this.
The Target deals +2d6 Damage.\nIf the Contractors dig into the Target's history, they'll learn how deadly they are.
In order to catch the Target off guard, the Contractors are going to need a really good plan."},
    "44": {"name": "Birthday Party", "payout_bonus": "0", "description": "Today is the Target's birthday.
You're really going to murder them today of all days?
Wow."},
    "45": {"name": "Performance Review", "payout_bonus": "1d6", "description": "The Handler and members of Slaughtr™ Quality Assurance are surreptitiously monitoring the Contractors and judging their performance like the petty tyrants they are.
When the Contract is complete, the Contractors will receive feedback in a deeply uncomfortable meeting.\nQA looks at several esoteric metrics, ranked from 1 to 6:\n● Bigness\n● Customer Service\n● Innovation\n● Zeitgeist\nA rank of 5 or lower on any of the above metrics is grounds for Punishment.
Rank 1 performances automatically result in Financial Penalty (-1d6 Payout per Rank 1).
Feel free to assign ranks arbitrarily."},
    "46": {"name": "The World is Red", "payout_bonus": "2d6", "description": "The Handler forgot to mention that several hundred pounds of uncut Rageroid got into the Target's ventilation system \"by accident,\" sending everyone nearby into a violent frenzy.\nOrganic Contractors double their Physick as long as they remain in the area but can't feel anything except anger.\nEnemies deal +2d6 Meat Damage with Melee weapons.
They're hyper aggressive and likely to fight one another and ignore danger."},
    "51": {"name": "Radiation Hazard", "payout_bonus": "1d6", "description": "Maybe a reactor leaked, or maybe the Build Bots dug up a of cache poorly labeled Old World trash.
The CHRIST can sort out low doses of radiation without issue.
Higher doses start to cause problems and that's exactly what the Contractors are dealing with.
Unlike the zeta rays produced by The Old Fashioned, gamma radiation is the gift that keeps on giving.
Don't expect to gain superpowers - radiation is universally harmful.\nThe Contractors don't know the Target's sector is irradiated.
It's on the GM to describe it and on the Contractors to put it together.\nWhen you're exposed to high levels of alpha, beta, or gamma radiation, your genome gets completely borked.
Roll twice on the Resurrection Quirk table each time you resurrect until you get your rads purged.
Doing so costs 8 Debt.\nDirect Exposure is the most dangerous type of exposure.
Each minute of Direct Exposure deals 3d6 Meat Damage. 3 minutes is a lethal dose, however victims will not die immediately.
Immediate death occurs after 10 minutes of Direct Exposure. Direct Exposure includes standing in an active reactor without protection, diving into certain glowing pools deep in the Sewers, or swallowing whole fuel rods.
You will die an agonizing death as your skin falls off and your gums melt within 12 hours of lethal Direct Exposure.
Gain 2 Stress from the agony.\nAmbient Exposure to strong radiation deals 1d6 Meat Damage to an exposed body part every 10 minutes.
2 hours of accumulated Ambient Exposure is generally fatal, with death occurring 3-4 days after rad absorption.
Ambient Exposure includes exploring irradiated tunnels without protective gear, drinking contaminated water, or eating the meat of glowing boars.
Somewhat unintuitively, Ambient Exposure is more painful at lethal doses than Direct Exposure; the slow death prolongs the victim's suffering.
When you die of Ambient Exposure, gain 4 Stress from the agony."},
    "52": {"name": "Deepfake", "payout_bonus": "0", "description": "The Contractors are being tricked into killing for free by nefarious hackers using widely available AI voice apps.
The \"Handler\" they spoke to was fake.\nThe Contractors are going to need to find a way to get some cash or they're out of luck.
The Handler might be able to help them track down the scammers."},
    "53": {"name": "Kill Fuck Requiem", "payout_bonus": "0", "description": "A past romantic partner of one of the Contractors appears out of the blue, involving themselves in the plot and potentially betraying the Contractors."},
    "54": {"name": "Secret Mutant", "payout_bonus": "2d6", "description": "The Target or one of their goons is heavily mutated (+3 Random Mutations)."},
    "55": {"name": "Secret Psychic", "payout_bonus": "2d6", "description": "The Target or one of their goons is a powerful Psionic (+3 Random Psionic Abilities)."},
    "56": {"name": 
"Not A Place Of Honour", "payout_bonus": "2d6", "description": "A nightmare from the past slumbers within the Target's location.
Every day Shoppers go about their business, unaware of the danger lurking just out of sight.
They pay little heed to the eroded pictograms and dead language warning of the danger.\nThe ancient hazard could be radiation, unfiltered mutagen, an unshackled AI, nerve gas, forgotten experiments, relics of the Ultra War, cryo-pods full of old GEN 2 Gene Warriors, malfunctioning warbots, or an Archangel trapped in a failing Psionic prison.
Whatever it is, it's deadly.\nUnleash the danger at the worst possible moment or when the Contractors stumble upon it."},
    "61": {"name": "Shapeshifter", "payout_bonus": "3d6", "description": "The Target can copy the appearance of nearby things and people, transforming themselves into chairs, coffee cups, guns, or trusted companions.
They are functionally identical to anything they mimic. They can roll or shuffle around awkwardly when in the form of inanimate objects."},
    "62": {"name": "The Combination Hamburger Store & Taco House", "payout_bonus": "0", "description": "Roll on the Location table twice.
The Target's Location is a mishmash of both results, even if it doesn't really make sense.
The HyperMall is full of strange and wonderful places built for unknown reasons."},
    "63": {"name": "Communist Sympathizer", "payout_bonus": "1d6", "description": "The Target maintains a secret shrine to the Seven Great Thinkers: Marx, Posadas, Effentrout, Lenin, Nergüi, Mao, Marblewax.
They possess extensive Ideological Contraband that must be destroyed before it poisons your mind.\nKilling the Target is not a criminal offense, however Contractors are likely to be interrogated to ensure Thought Purity."},
    "64": {"name": "*Hacker Voice* I'm In", "payout_bonus": "2d6", "description": "A Grey Hat Hacker hired by the Target is after the Contractors, pursuing them through MallNet and tracking their every move.\nUnless the Contractors eschew all technology more complicated than a handgun, the Grey Hat will be able to track them and relay that information back to the Target."},
    "65": {"name": "Inception", "payout_bonus": "2d6", 
"description": "The Contractors find themselves in media res on a difficult Contract.
Maybe they're taking fire or about to kill someone.\nThe secret is that they're inside the Target's dream.
They wake up when they die rather than resurrecting.\nWhen the Contractors wake up, they find themselves in a random location with an unconscious Target and a note detailing the information they need to extract from (or implant into) the Target's subconscious.
A Dreamworld Synergistician is there to help them get back into the Target's dream, which takes the form of the Contract you rolled.
Add weird dream elements as necessary.\nRoll 1d6 for the type of info they need to extract from (or implant into) the Target's subconscious:\n1.
Schematics\n2. Specific fears, Passions, or fabricated memories\n3. Manchurian conditioning\n4. Childhood trauma\n5. Passwords, treasure locations, floor plans, security strength\n6.
Business dealings"},
    "66": {"name": "Roll Twice", "payout_bonus": "0", "description": "If you get things that don't make sense together, reroll.
Or don't. Bosses love assigning impossible tasks."}
}

CONTRACT_SECURITY_GRADE = {
    "SG1": { "payout_bonus": "1d6", "options": { 1: "A handful of bodyguards", 2: "Cameras", 3: "Secure panic room", 4: "Squad of Grunt Pigs, Cultists, or other Mooks", 5: "A few Robots", 6: "Getaway Vehicle (Jetpack, monowheel, sports car)"}},
    "SG2": { "payout_bonus": "2d6", "options": { 1: "Autoturrets (2d6 Damage Machine Gun)", 2: "Laser Tripwires (3d6 Damage Explosion)", 3: "A Military-Grade Cyborg", 4: "A bunch of Biodrones", 5: "A small gang", 6: "A Jinxer"}},
    "SG3": { "payout_bonus": "3d6", "options": { 1: "Domesticated Sewer Gators", 2: 
"The local HMPD precinct", 3: "A handful of trained Gene Wolves", 4: "A squad of Gene Warriors", 5: "Psionic Commandos", 6: "A NANCY exomech"}},
    "SG4": { "payout_bonus": "4d6", "options": { 1: "Multiple squads of Gene Warriors or a squad of Military-Grade Cyborgs wielding Heavy Weapons", 2: "A Baba Yaga exomech", 3: "Expert sniper", 4: "A Jigsaw murder labyrinth cut off from the Resurrection Matrix", 5: "A cabal of Consumerist Priests", 6: "A gaggle of Executives with subordinates"}},
    "SG5": { "payout_bonus": "5d6", "options": { 1: "A private militia", 2: "A squad of NANCYs", 3: "A 
large gang, complete with vehicles, Heavy Weapons, and cobbled-together exomechs", 4: "A captured Angel, mystically bound to service", 5: "Pack of trained Gene Wolves", 6: "Lava Pits, Acid Vats, Toxic Gas, Cryo Blasters, etc."}},
    "SG6": { "payout_bonus": "6d6", "options": { 1: "An entire private army", 2: "An Archangel, to be unleashed as a last resort", 3: "A squad of Baba Yaga exomechs", 4: "The Gender Construct", 5: "AI or an expert Hacker coordinating everything", 6: "Air support, courtesy of the HyperMall Police Department"}}
}
# --- DATA: NPC ARCHETYPES ---
NPC_ARCHETYPES = {
    "Civvie": {"names": ["Bob", "Janet", "Kevin"], "stats": {"Physick": 1, "Savvy": 1, "Thinkitude": 1, "Craveability": 1}, "skills": [], "inventory": ["Useless Junk"], "meat_damage_max": 6, "stress_max": 4, "debt_max": 10, "behavior_type": "passive", "xp_reward": 1},
    "Wastelander": {"names": ["Scab", "Gutter", "Rat"], "stats": {"Physick": 2, "Savvy": 2, "Thinkitude": 1, "Craveability": 1}, "skills": ["Bash", "Knife"], "inventory": [{"name": "Shiv", "skill": "Knife"}], "meat_damage_max": 8, "stress_max": 
6, "debt_max": 15, "behavior_type": "aggressive", "xp_reward": 5},
    "Grunt Pig": {"names": ["Oinker", "Porky", "Squealer"], "stats": {"Physick": 3, "Savvy": 1, "Thinkitude": 1, "Craveability": 2}, "skills": ["Bash", "Pistol"], "inventory": [{"name": "Riot Baton", "skill": "Bash"}, {"name": "Funny Bone Pistol", "skill": "Pistol"}], "meat_damage_max": 12, "stress_max": 8, "debt_max": 20, "behavior_type": "aggressive", "xp_reward": 10},
    "Manager": {"names": ["Mr. Henderson", "Ms. Smith"], "stats": {"Physick": 1, "Savvy": 3, "Thinkitude": 2, "Craveability": 3}, "skills": ["Asskissing", "Corruption"], "inventory": ["Briefcase", "Useless Reports"], "meat_damage_max": 7, "stress_max": 12, "debt_max": 30, "behavior_type": "passive_aggressive", 
"xp_reward": 8},
    "Gene Warrior": {"names": ["Unit 734", "Subject Delta"], "stats": {"Physick": 4, "Savvy": 2, "Thinkitude": 1, "Craveability": 1}, "skills": ["Rifle", "Cyber Karate"], "inventory": [{"name": "Assault Rifle", "skill": "Rifle"}], "meat_damage_max": 15, "stress_max": 10, "debt_max": 25, "behavior_type": "aggressive", "xp_reward": 15},
     "Gun Nut": {"names": ["Trigger", "Bullet", "Gunther"], "stats": {"Physick": 2, "Savvy": 2, "Thinkitude": 1, "Craveability": 2}, "skills": ["Pistol", "Rifle", "Shotgun"], "inventory": [{"name": "Pistol", "skill": "Pistol"}, {"name": "Rifle", "skill": "Rifle"}], "meat_damage_max": 10, "stress_max": 8, "debt_max": 20, "behavior_type": "aggressive", "xp_reward": 12},
    "Cultist": {"names": ["Brother Abernathy", "Sister Ophelia"], "stats": {"Physick": 1, "Savvy": 1, "Thinkitude": 2, "Craveability": 4}, "skills": ["Worship The Consumer", "Knife"], "inventory": [{"name": "Sacrificial Dagger", "skill": "Knife"}, "Cult Robes"], "meat_damage_max": 8, "stress_max": 15, "debt_max": 25, "behavior_type": "fanatical", "xp_reward": 7}
}

# --- DATA: ROOM ARCHETYPES ---
ROOM_ARCHETYPES = {
    "Corridor": {"description": "A sterile, white corridor stretches into the distance. Fluorescent lights hum overhead.", "exits": {}, "item_spawn_chance": 0.1, "npc_spawn_info": {}},
    "NexusHub": {"description": "This is the bustling Nexus Hub. Screens display job postings and news feeds. A central fountain murmurs peacefully.", "exits": {}, "item_spawn_chance": 0.3, "npc_spawn_info": {"Wastelander": 0.2, "Civvie": 0.5}},
    "Cafeteria": {"description": "The smell of stale coffee and nutrient paste hangs heavy in the air. Tables are scattered around the room.", "exits": {}, "item_spawn_chance": 0.5, "npc_spawn_info": {"Civvie": 0.6, "Manager": 0.1}},
    "SecurityCheckpoint": {"description": "A formidable security checkpoint with automated turrets and scanner gates. Grunt Pigs stand guard.", "exits": {}, "item_spawn_chance": 0.1, "npc_spawn_info": {"Grunt Pig": 0.8}},
    "SecretLab": {"description": "A hidden laboratory filled with humming machinery and bubbling vats of green liquid. Strange symbols adorn the walls.", "exits": {}, "item_spawn_chance": 0.7, "npc_spawn_info": {"Gene Warrior": 0.3}},
    "Market": {"description": "A chaotic market filled with stalls selling everything from black market cybernetics to exotic pets.", "exits": {}, "item_spawn_chance": 0.8, "npc_spawn_info": {"Civvie": 0.4, "Wastelander": 0.3, "Gun Nut": 0.2}},
    "CultSanctum": {"description": "A dimly lit sanctum, walls adorned with unsettling symbols. An altar stands at the center, stained with something dark.", "exits": {}, "item_spawn_chance": 0.4, "npc_spawn_info": {"Cultist": 0.7}},
    "HabBlock": {"description": "A towering block of residential hab-pods. The air is thick with the scent of ozone and recycled air.", "exits": {}, "item_spawn_chance": 0.6, "npc_spawn_info": {"Civvie": 0.5, "Ganger": 0.2}},
    "Alley": {"description": "A dark, grimy alley littered with refuse. Strange liquids drip from overhead pipes.", "exits": {}, "item_spawn_chance": 0.9, "npc_spawn_info": {"Wastelander": 0.4, "Shoplifter": 0.3}}
}

# --- World & Mission Classes ---
class Contract:
    """Represents a job for players to undertake."""
    def __init__(self, contract_id, who, where, when, how, why, know, dont_know, payout):
        self.id = contract_id
        self.who = who
        self.where = where
        self.when = when
        self.how = how
        self.why = why
        self.know = know
        self.dont_know = dont_know
        self.payout = payout
        self.is_completed = False

    def get_full_description(self):
        """Returns a formatted string of the full contract details."""
        description = f"\n{C.BOLD}{C.MAGENTA}--- CONTRACT: {self.id} ---\n{C.RESET}"
        description += f"{C.YELLOW}Target:{C.RESET} {self.who['name']}\n"
        description += f"{C.YELLOW}Location:{C.RESET} {self.where['name']}\n"
        description += f"{C.YELLOW}Timeframe:{C.RESET} {self.when['name']}\n"
        description += f"{C.YELLOW}Method:{C.RESET} {self.how['name']}\n"
        description += f"{C.YELLOW}Reason:{C.RESET} {self.why}\n"
        description += f"{C.YELLOW}Known Intel:{C.RESET} {self.know['name']} - {self.know['description']}\n"
        description += f"{C.YELLOW}Handler's Suspicion:{C.RESET} {self.dont_know['name']} - {self.dont_know['description']}\n"
        description += f"{C.YELLOW}Payout:{C.RESET} {self.payout} Debt\n"
        return description

class Room:
    """Represents a single location in the game world."""
    def __init__(self, room_id, name, description, exits=None):
        self.id = room_id
        self.name = name
        self.description = description
        self.exits = exits if exits else {}
        self.player_ids = []
        self.npc_ids = []
        self.item_ids = [] # Holds IDs of items on the floor

    def get_description(self):
        """Returns the full description of the room, including occupants and items."""
        return f"{C.BOLD}{C.CYAN}{self.name}{C.RESET}\n{self.description}"

class GameWorld:
    """Manages all the rooms and the overall world state."""
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.rooms = {}
        # A simple world layout for demonstration
        self.world_layout = {
            "NEXUS_HUB": {"archetype": "NexusHub", "exits": {"north": "MARKET", "east": "CORRIDOR_EAST", "south": "HAB_BLOCK_A"}},
            "MARKET": {"archetype": "Market", "exits": {"south": "NEXUS_HUB", "west": "ALLEY"}},
            "ALLEY": {"archetype": "Alley", "exits": {"east": "MARKET"}},
            "CORRIDOR_EAST": {"archetype": "Corridor", "exits": {"west": "NEXUS_HUB", "east": "SECURITY_A"}},
            "SECURITY_A": {"archetype": "SecurityCheckpoint", "exits": {"west": "CORRIDOR_EAST", "east": "SECRET_LAB"}},
            "SECRET_LAB": {"archetype": "SecretLab", "exits": {"west": "SECURITY_A"}},
            "HAB_BLOCK_A": {"archetype": "HabBlock", "exits": {"north": "NEXUS_HUB", "south": "CAFETERIA"}},
            "CAFETERIA": {"archetype": "Cafeteria", "exits": {"north": "HAB_BLOCK_A"}}
        }

    def spawn_world(self):
        """Creates the rooms and their connections based on the world layout."""
        for room_id, room_data in self.world_layout.items():
            archetype_key = room_data["archetype"]
            archetype = ROOM_ARCHETYPES.get(archetype_key, ROOM_ARCHETYPES["Corridor"])
            
            new_room = Room(
                room_id=room_id,
                name=room_id.replace("_", " ").title(),
                description=archetype["description"],
                exits=room_data["exits"]
            )
            self.rooms[new_room.id] = new_room

            # --- ITEM SPAWNING LOGIC (Step 4) ---
            spawn_chance = archetype.get("item_spawn_chance", 0)
            if random.random() < spawn_chance:
                # This will call a method to be added in GameManager in the next chunk.
                # It creates a generic item for now.
                item_data = {
                    "name": f"Scrap-{secrets.token_hex(2)}",
                    "description": "A piece of seemingly worthless junk. Could be useful for crafting.",
                    "type": "misc"
                }
                item_id = self.game_manager.create_item(item_data)
                if item_id:
                    new_room.item_ids.append(item_id)
# --- Game Logic Managers ---
class CombatManager:
    """Manages all combat encounters."""
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.active_combats = {}  # room_id -> combat_state
        self.pending_actions = {} # character_id -> {action: str, ...}

    def is_character_in_combat(self, character_id):
        """Checks if a character is in any active combat."""
        for combat in self.active_combats.values():
            if character_id in combat['participants']:
                return True
        return False

    def is_character_turn(self, character_id):
        """Checks if it is currently the character's turn in their combat."""
        for combat in self.active_combats.values():
            if character_id in combat['participants']:
                if combat['turn_queue'] and combat['turn_queue'][0] == character_id:
                    return True
        return False

    def start_combat(self, room_id, initiator_id, target_id):
        """Initializes a new combat encounter in a room."""
        if room_id in self.active_combats:
            # Combat already active, add participants if not already in
            if initiator_id not in self.active_combats[room_id]['participants']:
                self.active_combats[room_id]['participants'].append(initiator_id)
                self.active_combats[room_id]['turn_queue'].append(initiator_id)
            if target_id not in self.active_combats[room_id]['participants']:
                self.active_combats[room_id]['participants'].append(target_id)
                self.active_combats[room_id]['turn_queue'].append(target_id)
            return

        room = self.game_manager.world.rooms.get(room_id)
        if not room: return

        participants = [p_id for p_id in room.player_ids + room.npc_ids if not self.game_manager.get_character_by_id(p_id).is_dead]
        
        if len(participants) < 2: return

        self.game_manager.broadcast_message(f"{C.RED}{C.BOLD}Combat has begun!{C.RESET}", "combat", room_id)
        
        # Give initiative bonus to initiator, then shuffle
        turn_order = [p_id for p_id in participants if p_id != initiator_id]
        random.shuffle(turn_order)
        turn_order.insert(0, initiator_id)

        self.active_combats[room_id] = {
            'participants': participants,
            'turn_queue': deque(turn_order),
            'start_time': time.time()
        }
        
        # Notify the first person it's their turn
        first_in_turn_id = self.active_combats[room_id]['turn_queue'][0]
        actor = self.game_manager.get_character_by_id(first_in_turn_id)
        if isinstance(actor, Player):
            self.game_manager.send_message_to_player(first_in_turn_id, f"\n{C.GREEN}It's your turn to act.{C.RESET}")

    def end_combat(self, room_id):
        """Ends a combat encounter."""
        if room_id in self.active_combats:
            del self.active_combats[room_id]
            self.game_manager.broadcast_message(f"{C.GREEN}Combat has ended.{C.RESET}", "combat", room_id)

    def resolve_attack(self, attacker_id, target_id, skill_used):
        # This function remains largely the same, but it's now called by update_all_combats
        attacker = self.game_manager.get_character_by_id(attacker_id)
        target = self.game_manager.get_character_by_id(target_id)
        if not attacker or not target or target.is_dead: return

        self.game_manager.broadcast_message(f"{attacker.name} attacks {target.name} using {C.MAGENTA}{skill_used}{C.RESET}!", "combat", attacker.current_room_id)
        time.sleep(0.5)

        # Simplified dice roll for now
        skill_level = attacker.skills.get(skill_used, 1)
        stat_level = attacker.stats["Physick"] # default stat
        dice_pool = skill_level + stat_level
        successes = sum(1 for _ in range(dice_pool) if random.randint(1, 6) >= 4)

        if successes > 0:
            damage = successes * 2 # Example damage calculation
            target.current_meat_damage += damage
            self.game_manager.broadcast_message(f"{C.RED}{target.name} takes {damage} meat damage!{C.RESET}", "combat", attacker.current_room_id)
            if target.current_meat_damage >= target.meat_damage_max:
                target.is_dead = True
                self.game_manager.handle_death(target)
        else:
            self.game_manager.broadcast_message(f"{attacker.name}'s attack misses!", "combat", attacker.current_room_id)

    def remove_character_from_combat(self, character_id, room_id):
        """Removes a character who has fled or died from a combat instance."""
        if room_id in self.active_combats:
            combat = self.active_combats[room_id]
            if character_id in combat['participants']:
                combat['participants'].remove(character_id)
            # Use a new deque to safely remove from the turn queue
            combat['turn_queue'] = deque([p for p in combat['turn_queue'] if p != character_id])

    def update_all_combats(self):
        """The new core of combat, processing one action per update tick for all combats."""
        for room_id, combat in list(self.active_combats.items()):
            if len(combat['participants']) < 2:
                self.end_combat(room_id)
                continue

            if not combat['turn_queue']: # Repopulate queue if it's empty
                alive_participants = [p for p in combat['participants'] if not self.game_manager.get_character_by_id(p).is_dead]
                if len(alive_participants) < 2:
                    self.end_combat(room_id)
                    continue
                combat['turn_queue'].extend(alive_participants)

            current_actor_id = combat['turn_queue'][0]
            actor = self.game_manager.get_character_by_id(current_actor_id)

            if not actor or actor.is_dead:
                combat['turn_queue'].popleft()
                continue
            
            acted = False
            # --- Player Action Processing (Step 1) ---
            if isinstance(actor, Player):
                if current_actor_id in self.pending_actions:
                    action = self.pending_actions.pop(current_actor_id)
                    if action['action'] == 'attack':
                        self.resolve_attack(current_actor_id, action['target'], action['skill'])
                    elif action['action'] == 'flee_success':
                         self.game_manager.broadcast_message(f"{actor.name} successfully escapes from combat!", "combat", room_id)
                         self.remove_character_from_combat(actor.id, room_id)
                    elif action['action'] == 'flee_failure':
                        self.game_manager.broadcast_message(f"{C.YELLOW}{actor.name} tries to flee, but fails!{C.RESET}", "combat", room_id)
                    
                    acted = True

            # --- NPC Action Processing (Step 7) ---
            else: # It's an NPC
                time.sleep(1) # Dramatic pause for NPC "thinking"
                player_targets = [p_id for p_id in combat['participants'] if isinstance(self.game_manager.get_character_by_id(p_id), Player) and not self.game_manager.get_character_by_id(p_id).is_dead]
                if player_targets:
                    target_id = random.choice(player_targets)
                    
                    # Enhanced AI: Choose best skill
                    # Simple version: prefer weapon skills over bash
                    available_skills = [skill for skill, level in actor.skills.items() if level > 0 and skill in ["Pistol", "Rifle", "Axe", "Knife", "Bash"]]
                    skill_to_use = random.choice(available_skills) if available_skills else "Bash"

                    self.resolve_attack(current_actor_id, target_id, skill_to_use)
                    acted = True
                else: # No players left in combat
                    self.end_combat(room_id)
                    continue
            
            if acted:
                combat['turn_queue'].rotate(-1)
                # Check if combat should end
                players_alive = any(isinstance(self.game_manager.get_character_by_id(p), Player) and not self.game_manager.get_character_by_id(p).is_dead for p in combat['participants'])
                npcs_alive = any(isinstance(self.game_manager.get_character_by_id(p), NPC) and not self.game_manager.get_character_by_id(p).is_dead for p in combat['participants'])

                if not players_alive or not npcs_alive:
                    self.end_combat(room_id)
                    continue

                # Notify next player it's their turn
                next_actor_id = combat['turn_queue'][0]
                next_actor = self.game_manager.get_character_by_id(next_actor_id)
                if isinstance(next_actor, Player):
                    self.game_manager.send_message_to_player(next_actor_id, f"\n{C.GREEN}It's your turn to act.{C.RESET}")


class GameManager:
    """Handles all major game systems and player commands."""
    def __init__(self):
        self.players = {}
        self.npcs = {}
        self.world = GameWorld(self)
        self.combat_manager = CombatManager(self)
        self.active_contracts = []
        self.next_player_id = 1
        self.next_npc_id = 1
        self.world_items = {} # All item instances are stored here
        self.next_item_id = 1
    
    # --- Persistence Functions (Step 2) ---
    def save_player(self, player_id):
        """Saves a single player's data to a JSON file."""
        player = self.players.get(player_id)
        if not player: return
        
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            save_path = os.path.join(SAVE_DIR, f"{player.name}.json")
            with open(save_path, 'w') as f:
                json.dump(player.to_dict(), f, indent=4)
            print(f"{C.GREEN}Saved character data for {player.name}.{C.RESET}")
        except Exception as e:
            print(f"{C.RED}Error saving character {player.name}: {e}{C.RESET}")
            
    def save_all_players(self):
        """Iterates and saves all currently connected players."""
        for player_id in list(self.players.keys()):
            self.save_player(player_id)

    def load_player(self, username, conn):
        """Loads a player's data from a file if it exists."""
        save_path = os.path.join(SAVE_DIR, f"{username}.json")
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f:
                    player_data = json.load(f)
                    # Use a dummy ID and conn for from_dict, then update
                    player = Player.from_dict(player_data)
                    player.conn = conn # Re-attach the live connection
                    self.players[player.id] = player
                    
                    # Put player back in their last room
                    room = self.world.rooms.get(player.current_room_id)
                    if room:
                        room.player_ids.append(player.id)
                    
                    print(f"{C.GREEN}Loaded character data for {username}.{C.RESET}")
                    return player
            except Exception as e:
                print(f"{C.RED}Error loading character {username}: {e}{C.RESET}")
                return None
        return None

    # --- Item Functions (Step 4) ---
    def create_item(self, item_data):
        """Creates a new item instance and stores it."""
        item_id = f"item_{self.next_item_id}"
        self.next_item_id += 1
        self.world_items[item_id] = item_data
        return item_id

    def get_item_name(self, item_id):
        """Gets an item's name from its ID."""
        return self.world_items.get(item_id, {}).get("name", "Unknown Item")

    # --- Game State & Command Handling ---
    def generate_contract(self):
        """Generates a new random contract. (Payout calculation fixed)."""
        who = random.choice(list(CONTRACT_WHO.values()))
        where = random.choice(list(CONTRACT_WHERE.values()))
        when = random.choice(list(CONTRACT_WHEN.values()))
        how = random.choice(list(CONTRACT_HOW.values()))
        why = random.choice(list(CONTRACT_WHY.values()))
        know = random.choice(list(CONTRACT_KNOW.values()))
        dont_know = random.choice(list(CONTRACT_DONT_KNOW.values()))

        # --- Payout Calculation Fix (Step 3) ---
        payout = 0
        payout += parse_dice_formula(who.get('payout_bonus', '0'))
        payout += parse_dice_formula(where.get('payout_bonus', '0'))
        payout += parse_dice_formula(when.get('payout_bonus', '0'))
        payout += parse_dice_formula(how.get('payout_bonus', '0'))
        payout += parse_dice_formula(know.get('payout_bonus', '0'))
        # Payout for security grade
        for sg_key in where.get("sg", []):
            if sg_key in CONTRACT_SECURITY_GRADE:
                payout += parse_dice_formula(CONTRACT_SECURITY_GRADE[sg_key].get('payout_bonus', '0'))

        new_contract = Contract(f"CON-{len(self.active_contracts)+1}", who, where, when, how, why, know, dont_know, payout)
        self.active_contracts.append(new_contract)
        # For demonstration, broadcast the new contract to everyone
        self.broadcast_message(f"\n{C.BOLD}{C.YELLOW}New contract available!{C.RESET}", "system")
        self.broadcast_message(new_contract.get_full_description(), "system")
    
    # --- Command Handler Modifications ---
    
    def handle_attack(self, player_id, args):
        """Handles a player's attack command under the new turn-based system."""
        player = self.players.get(player_id)
        if not player or not args:
            self.send_message_to_player(player_id, "Attack who?")
            return

        if not self.combat_manager.is_character_in_combat(player_id):
            self.send_message_to_player(player_id, "You are not in combat.")
            return

        if not self.combat_manager.is_character_turn(player_id):
            self.send_message_to_player(player_id, f"{C.YELLOW}It's not your turn!{C.RESET}")
            return
            
        target_name = args[0]
        room = self.world.rooms.get(player.current_room_id)
        target_id = None
        for npc_id in room.npc_ids:
            if self.npcs[npc_id].name.lower() == target_name.lower():
                target_id = npc_id
                break
        
        if not target_id:
            self.send_message_to_player(player_id, "You don't see them here.")
            return

        skill_to_use = "Bash" # Default, could be expanded with 'attack <target> with <weapon/skill>'
        
        # --- Register Action (Step 1) ---
        self.combat_manager.pending_actions[player_id] = {'action': 'attack', 'target': target_id, 'skill': skill_to_use}
        self.send_message_to_player(player_id, f"You ready your attack against {target_name}...")

    def handle_get(self, player_id, args):
        """Handles the get/take command."""
        player = self.players.get(player_id)
        if not player or not args:
            self.send_message_to_player(player_id, "Get what?")
            return
        
        item_name_to_get = " ".join(args).lower()
        room = self.world.rooms.get(player.current_room_id)
        item_id_to_get = None

        for item_id in room.item_ids:
            if self.get_item_name(item_id).lower() == item_name_to_get:
                item_id_to_get = item_id
                break
        
        if item_id_to_get:
            room.item_ids.remove(item_id_to_get)
            player.inventory.append(item_id_to_get) # inventory now holds IDs
            item_name = self.get_item_name(item_id_to_get)
            self.send_message_to_player(player_id, f"You take the {item_name}.")
            self.broadcast_message(f"{player.name} takes the {item_name}.", "room", room.id, exclude_player_id=player_id)
        else:
            self.send_message_to_player(player_id, "You don't see that here.")

    def handle_drop(self, player_id, args):
        """Handles the drop command."""
        player = self.players.get(player_id)
        if not player or not args:
            self.send_message_to_player(player_id, "Drop what?")
            return

        item_name_to_drop = " ".join(args).lower()
        room = self.world.rooms.get(player.current_room_id)
        item_id_to_drop = None

        for item_id in player.inventory:
            if self.get_item_name(item_id).lower() == item_name_to_drop:
                item_id_to_drop = item_id
                break

        if item_id_to_drop:
            player.inventory.remove(item_id_to_drop)
            room.item_ids.append(item_id_to_drop)
            item_name = self.get_item_name(item_id_to_drop)
            self.send_message_to_player(player_id, f"You drop the {item_name}.")
            self.broadcast_message(f"{player.name} drops the {item_name}.", "room", room.id, exclude_player_id=player_id)
        else:
            self.send_message_to_player(player_id, "You don't have that.")
    
    def handle_flee(self, player_id, args):
        """Handles the flee command."""
        player = self.players.get(player_id)
        if not player: return

        if not self.combat_manager.is_character_in_combat(player_id):
            self.send_message_to_player(player_id, "You're not in combat.")
            return

        if not self.combat_manager.is_character_turn(player_id):
            self.send_message_to_player(player_id, f"{C.YELLOW}It's not your turn!{C.RESET}")
            return
            
        # Skill check: Savvy + Running
        skill_check_value = player.stats.get('Savvy', 1) + player.skills.get('Running', 0)
        successes = sum(1 for _ in range(skill_check_value) if random.randint(1, 6) >= 5) # Harder check for flee

        current_room_id = player.current_room_id
        current_room = self.world.rooms[current_room_id]

        if successes > 0:
            if current_room.exits:
                # Flee to a random valid exit
                flee_exit = random.choice(list(current_room.exits.keys()))
                new_room_id = current_room.exits[flee_exit]
                
                # Move player
                current_room.player_ids.remove(player_id)
                self.world.rooms[new_room_id].player_ids.append(player_id)
                player.current_room_id = new_room_id
                
                # Register success action to advance turn
                self.combat_manager.pending_actions[player_id] = {'action': 'flee_success'}
                
                self.send_message_to_player(player_id, f"You successfully flee {flee_exit} to {self.world.rooms[new_room_id].name}!")
                # Immediately show the new room description
                self.handle_look(player_id, [])
            else:
                # No exits, can't flee
                self.combat_manager.pending_actions[player_id] = {'action': 'flee_failure'}
                self.send_message_to_player(player_id, "There's nowhere to flee!")
        else:
            # Failed flee, register failure action
            self.combat_manager.pending_actions[player_id] = {'action': 'flee_failure'}
            self.send_message_to_player(player_id, "You try to escape, but can't find an opening!")
    
    def handle_tell(self, player_id, args):
        """Handles private player-to-player messages."""
        sender = self.players.get(player_id)
        if not sender or len(args) < 2:
            self.send_message_to_player(player_id, "Tell who what? Usage: tell <player> <message>")
            return
            
        target_name = args[0].lower()
        message_text = " ".join(args[1:])
        
        target_player = None
        for p in self.players.values():
            if p.name.lower() == target_name:
                target_player = p
                break
        
        if target_player:
            self.send_message_to_player(target_player.id, f"{C.CYAN}{sender.name} tells you, \"{message_text}\"{C.RESET}")
            self.send_message_to_player(sender.id, f"{C.CYAN}You tell {target_player.name}, \"{message_text}\"{C.RESET}")
        else:
            self.send_message_to_player(player_id, f"Could not find a player named '{args[0]}' online.")

    # --- Other handlers (snipped for brevity, they are in the original file and don't need major changes for these steps) ---
    # ... handle_look, handle_say, handle_help, etc. ...
    # We will need to modify handle_look and handle_inventory though.

    def handle_look(self, player_id, args):
        player = self.players.get(player_id)
        if not player: return
        room = self.world.rooms.get(player.current_room_id)
        if not room: return

        # Room description
        self.send_message_to_player(player_id, room.get_description())

        # Show items on the ground
        if room.item_ids:
            item_names = [self.get_item_name(item_id) for item_id in room.item_ids]
            self.send_message_to_player(player_id, f"{C.GREEN}You see here: {', '.join(item_names)}.{C.RESET}")

        # Show other players and NPCs
        occupants = []
        for p_id in room.player_ids:
            if p_id != player_id:
                occupants.append(self.players[p_id].name)
        for npc_id in room.npc_ids:
            occupants.append(self.npcs[npc_id].name)

        if occupants:
            self.send_message_to_player(player_id, f"{C.YELLOW}Also here: {', '.join(occupants)}.{C.RESET}")
        
        self.send_message_to_player(player_id, f"Exits: {', '.join(room.exits.keys()) if room.exits else 'None'}")
    
    def handle_inventory(self, player_id, args):
        player = self.players.get(player_id)
        if not player: return
        if not player.inventory:
            self.send_message_to_player(player_id, "You are not carrying anything.")
            return

        inventory_list = [self.get_item_name(item_id) for item_id in player.inventory]
        self.send_message_to_player(player_id, f"You are carrying: {', '.join(inventory_list)}")
        
    def handle_help(self, player_id, args):
        """Displays help information, now including new commands."""
        help_text = f"""
{C.BOLD}{C.YELLOW}Hypermud Commands:{C.RESET}
  say <message>        - Say something to the room.
  look                 - Look at your surroundings.
  attack <target>      - Attack a target in combat.
  get/take <item>      - Pick up an item from the room.
  drop <item>          - Drop an item from your inventory.
  inventory            - Check what you are carrying.
  flee                 - Attempt to escape from combat.
  tell <player> <msg>  - Send a private message.
  help                 - Show this help message.
  quit                 - Quit the game.
"""
        self.send_message_to_player(player_id, help_text)

    def handle_sheet(self, player_id, args):
        """Gathers character sheet data and sends it to the client for the UI."""
        player = self.players.get(player_id)
        if not player: return

        # Gather the data into a dictionary
        sheet_data = {
            "name": player.name,
            "background": player.background_name,
            "stats": player.stats,
            "skills": {k: v for k, v in player.skills.items() if v > 0},
            "health": f"{player.current_meat_damage} / {player.meat_damage_max}",
            "stress": f"{player.current_stress} / {player.stress_max}",
            "debt": f"{player.current_debt} / {player.debt_max}"
        }
        # Convert the dictionary to a JSON string
        json_payload = json.dumps(sheet_data)

        # Send the data to the client with the special prefix
        message = f"UI_DATA::sheet::{json_payload}"
        self.send_message_to_player(player_id, message)

    def handle_contracts_ui(self, player_id, args):
        """Gathers available contracts and sends them to the client for the UI."""
        # Gather data for all available contracts
        contracts_data = []
        for contract in self.active_contracts:
            # You might want to add a check here, e.g., if contract.status == "Available"
            contracts_data.append({
                "id": contract.id,
                "who": {"name": contract.who['name']},
                "where": {"name": contract.where['name']},
                "how": {"name": contract.how['name']},
                "payout": contract.payout
            })

        # Convert the list of contracts to a JSON string
        json_payload = json.dumps(contracts_data)

        # Send the data to the client with the special prefix
        message = f"UI_DATA::contracts::{json_payload}"
        self.send_message_to_player(player_id, message)
        
    def handle_death(self, character):
        """Handles the death of a character."""
        self.broadcast_message(f"{C.RED}{C.BOLD}{character.name} has died!{C.RESET}", "system", character.current_room_id)
        if isinstance(character, Player):
            # Simplified respawn logic
            self.send_message_to_player(character.id, "You feel your consciousness fade... and then re-form. You have been resurrected.")
            character.current_meat_damage = 0
            character.is_dead = False
        else: # NPC
            # Remove NPC from game
            room = self.world.rooms.get(character.current_room_id)
            if room and character.id in room.npc_ids:
                room.npc_ids.remove(character.id)
            if character.id in self.npcs:
                del self.npcs[character.id]
    
    # Placeholder for other existing functions from the original file
    def get_character_by_id(self, char_id):
        if char_id in self.players: return self.players[char_id]
        if char_id in self.npcs: return self.npcs[char_id]
        return None
        
    def send_message_to_player(self, player_id, message):
        player = self.players.get(player_id)
        if player and player.conn:
            try:
                player.conn.sendall(f"{message}\n".encode('utf-8'))
            except (OSError, BrokenPipeError):
                # Handle disconnected client
                pass

    def broadcast_message(self, message, msg_type="system", room_id=None, exclude_player_id=None):
        if room_id:
            room = self.world.rooms.get(room_id)
            if not room: return
            for p_id in room.player_ids:
                if p_id != exclude_player_id:
                    self.send_message_to_player(p_id, message)
        else: # Broadcast to all players
             for p_id in self.players:
                if p_id != exclude_player_id:
                    self.send_message_to_player(p_id, message)

    def spawn_npc_in_room(self, room_id, archetype_key):
        npc_id = f"npc_{self.next_npc_id}"
        self.next_npc_id += 1
        npc = NPC(npc_id, archetype_key, room_id)
        self.npcs[npc_id] = npc
        self.world.rooms[room_id].npc_ids.append(npc_id)
class GameServer:
    """The main server class that handles connections and the game loop."""
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {} # conn -> player_id
        self.running = True
        self.game_manager = GameManager()
        self.command_queue = queue.Queue()

    def start(self):
        """Starts the server, listens for connections, and runs the main loop."""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_CONNECTIONS)
        print(f"{C.GREEN}Server started on {self.host}:{self.port}{C.RESET}")

        # Start a thread to process commands
        command_thread = threading.Thread(target=self.process_commands)
        command_thread.daemon = True
        command_thread.start()

        # Start a thread for game state updates (like combat)
        update_thread = threading.Thread(target=self.game_update_loop)
        update_thread.daemon = True
        update_thread.start()

        try:
            while self.running:
                conn, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                client_handler = threading.Thread(target=self.client_thread, args=(conn,))
                client_handler.daemon = True
                client_handler.start()
        except OSError:
            if not self.running:
                print("Server socket closed as part of shutdown.")
            else:
                raise

    def game_update_loop(self):
        """A loop that runs periodically to update game state, e.g., combat."""
        while self.running:
            self.combat_manager.update_all_combats()
            time.sleep(0.5) # Update tick rate

    def process_commands(self):
        """Processes commands from the queue in the main thread."""
        while self.running:
            try:
                player_id, command, args = self.command_queue.get(timeout=1)
                
                command_map = {
                    "say": self.game_manager.handle_say,
                    "look": self.game_manager.handle_look,
                    "attack": self.game_manager.handle_attack,
                    "get": self.game_manager.handle_get,
                    "take": self.game_manager.handle_get, # Alias for get
                    "drop": self.game_manager.handle_drop,
                    "i": self.game_manager.handle_inventory,
                    "inventory": self.game_manager.handle_inventory,
                    "flee": self.game_manager.handle_flee,
                    "tell": self.game_manager.handle_tell,
                    "help": self.game_manager.handle_help,

'sheet': self.game_manager.handle_sheet,
'contracts': self.game_manager.handle_contracts_ui,

                    # Add other commands here
                }
                
                handler = command_map.get(command)
                if handler:
                    handler(player_id, args)
                else:
                    self.send_to_client_by_id(player_id, "Unknown command. Type 'help' for a list.")
                self.command_queue.task_done()
            except queue.Empty:
                continue

    def client_thread(self, conn):
        """Handles a single client connection."""
        self.send_to_client(conn, f"{C.BOLD}{C.YELLOW}Welcome to Hypermud!{C.RESET}")
        
        try:
            self.send_to_client(conn, "Enter your username: ")
            username = conn.recv(1024).decode('utf-8').strip()

            if not username or not re.match("^[A-Za-z0-9]+$", username):
                self.send_to_client(conn, "Invalid username. Disconnecting.")
                conn.close()
                return

            # --- Player Loading Logic (Step 2) ---
            player = self.game_manager.load_player(username, conn)

            if player:
                # Player was loaded from file
                self.clients[conn] = player.id
                self.send_to_client(conn, f"\nWelcome back, {C.BOLD}{username}{C.RESET}. Your character has been loaded.")
                self.game_manager.broadcast_message(f"{C.YELLOW}{player.name} has connected.{C.RESET}", "system", player.current_room_id, exclude_player_id=player.id)
                self.game_manager.handle_look(player.id, [])
            else:
                # New character creation process
                self.send_to_client(conn, f"\nCreating a new character for {C.BOLD}{username}{C.RESET}.")
                player_id = f"player_{self.game_manager.next_player_id}"
                self.game_manager.next_player_id += 1

                # For simplicity, we'll assign a random background. A real server would have a selection process.
                random_bg_code = random.choice(list(BACKGROUNDS.keys()))
                player = Player(player_id, username, random_bg_code, conn, "NEXUS_HUB")
                player.apply_background(BACKGROUNDS[random_bg_code])
                
                self.game_manager.players[player.id] = player
                self.clients[conn] = player.id
                self.world.rooms["NEXUS_HUB"].player_ids.append(player_id)
                
                self.send_to_client(conn, f"You are a {C.MAGENTA}{player.background_name}{C.RESET}. Good luck.")
                self.game_manager.broadcast_message(f"{C.YELLOW}{player.name} has entered the HyperMall.{C.RESET}", "system", "NEXUS_HUB", exclude_player_id=player.id)
                self.game_manager.handle_look(player.id, [])

            # Main game loop for the client
            while self.running and player.conn:
                self.send_to_client(conn, "> ")
                data = conn.recv(1024).decode('utf-8').strip()
                if not data:
                    break
                
                parts = data.split()
                command = parts[0].lower()
                args = parts[1:]

                if command == 'quit':
                    self.game_manager.save_player(player.id) # Save on quit
                    break
                
                self.command_queue.put((player.id, command, args))

        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {conn.getpeername()} disconnected unexpectedly.")
        finally:
            self.remove_client(conn)

    def remove_client(self, conn):
        """Removes a client from the server and saves their data."""
        player_id = self.clients.get(conn)
        if player_id:
            # --- Save Player on Disconnect (Step 2) ---
            self.game_manager.save_player(player_id)
            player = self.game_manager.players.get(player_id)
            if player:
                room = self.game_manager.world.rooms.get(player.current_room_id)
                if room and player_id in room.player_ids:
                    room.player_ids.remove(player_id)
                
                self.game_manager.broadcast_message(f"{player.name} has disconnected.", "system", player.current_room_id)
                
                # Remove from combat if they are in one
                self.game_manager.combat_manager.remove_character_from_combat(player_id, player.current_room_id)

                if player_id in self.game_manager.players:
                    del self.game_manager.players[player_id]
            
            if conn in self.clients:
                del self.clients[conn]
        
        try:
            conn.close()
        except OSError:
            pass

    def stop(self):
        """Shuts down the server gracefully, saving all players."""
        self.running = False
        print(f"\n{C.YELLOW}Server shutting down. Saving all players...{C.RESET}")
        self.game_manager.save_all_players() # Save all players on shutdown
        for conn in list(self.clients.keys()):
            try:
                conn.close()
            except OSError:
                pass
        self.server_socket.close()
        print(f"{C.YELLOW}Server has been shut down.{C.RESET}")

# --- Main execution block ---
if __name__ == "__main__":
    # Ensure save directory exists
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    server = GameServer(HOST, PORT)
    
    # Generate a world and some initial content
    server.game_manager.world.spawn_world()
    server.game_manager.spawn_npc_in_room("SECURITY_A", "Grunt Pig")
    server.game_manager.spawn_npc_in_room("ALLEY", "Wastelander")
    server.game_manager.generate_contract()

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"{C.RED}An unexpected error occurred: {e}{C.RESET}")
        server.stop()
