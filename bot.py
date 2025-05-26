import discord
import json
import asyncio
import os

from dotenv import load_dotenv
from typing import Optional
from typing import Literal
from collections import defaultdict
from datetime import datetime

from discord import app_commands 
from discord.app_commands import Choice
from discord.ext import commands
from discord.ui import View, Button

# Variable globale
load_dotenv()  # Charge les variables du fichier .env
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
user_stats = {}
fichier = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Pour voir les membres du serveur

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    global user_stats
    global fichier
    
    print(f'Bot connecté sous {bot.user}')

    for guild in bot.guilds:
        #Suppression des commandes sur un serveur spécifique (guild = serveur)
        #bot.tree.clear_commands(guild = guild)
        #Initialisation des droit des Admin
        load_json(guild.id)
        user_stats.setdefault(guild.id, {}).setdefault("169586520989106176", {})["droit"] = {"add": True, "clean": True, "token": True}
        save_json(user_stats.get(guild.id), guild.id)
        
        server_sync = await bot.tree.sync(guild=discord.Object(id=guild.id))
        server_command_names = ", ".join([cmd.name for cmd in server_sync])

        print(f"Commandes réinitialisées pour le serveur : {guild.name} (ID: {guild.id}). Commande : {server_command_names}")
        #Work#print(user_stats.setdefault(guild.id, {}).setdefault("169586520989106176", {})["droit"])
        
    try:
        synced = await bot.tree.sync()
        command_names = ", ".join([cmd.name for cmd in synced])
        print(f"✅ {len(synced)} slash command(s) synchronisées avec succès ! Commande : {command_names}")
    except Exception as e:
        print(f"⚠️ Erreur de sync des commandes: {e}")

@bot.event
async def on_guild_join(guild):

    print(f"{bot.user} a rejoint la guild: {guild.name} (ID: {guild.id})")
    
    await bot.tree.clear_commands(guild=guild)  # Effacer les commandes pour cette guild
    await bot.tree.sync()  # Ré-enregistrer les commandes
    print(f"Commandes réenregistrées pour la guild {guild.name}")
    
    channel = discord.utils.get(guild.text_channels, name='hall')
    if channel:
        await channel.send(
            "B-bonjours bonsoir... Je suis la nouvelle archiviste de la Ero. Heureuse de vous aidé à retrouvé vos papier d'admition et autre utilitaire."
        )
        
#
####Gestion des Perso####
#
@bot.tree.command(name="add", description="Ajoute un personnage.")
@app_commands.guilds(
    discord.Object(id=666059235070574593),  # ID de ton serveur 1
    discord.Object(id=1362186859819565266)   # ID de ton serveur 2
)
@app_commands.describe(
    nom=" du personnage",
    sexe=" du personnage",
    orientation=" du personnage",
    role=" du personnage",
    fiche="Lien de la fiche",
    user="À qui tu veux ajouter le persos'"
)

async def ajout_perso(
    interaction: discord.Interaction,
    nom: str,
    sexe: Literal["Homme","Femme"],
    orientation: Literal["aux Hommes","aux Femmes","aux Deux"],
    # Optionel a remplire, mais se rempliront auto si non
    role: Optional[Literal["Élève","Personnel","Autre"]] = None,
    fiche: Optional[str] = None,
    user: Optional[discord.Member] = None  
):
    await interaction.response.defer()  # Signale que la commande est en traitement
    ##Variables##
    global user_stats
    ROLE_MAPPING = {
        "Élève": 767402619537981460,     # ID du rôle "Élève"
        "Personnel": 767402536549744672, # ID du rôle "Personnel"
        "Autre": 767404122529202237,      # ID du rôle "Civil"
        "Multi": 844599390143250452,      # ID du rôle "Civil"
    }
    stats = load_json(interaction.guild.id)
    if role is None:
        salon = interaction.channel.parent
        #print("catégori: "+salon.name)
        match salon.name:
            case "élèves":
                role = "Élève"
            case "personnel-de-la-ero":
                role = "Personnel"
            case "hors-la-ero":
                role = "Autre"
        #print("role: "+role)
    if not await verif_droit(interaction, stats, "add"):
        return
    
    ##Valider le User##
    for_user = user
    #Check si on est dans un fil, prendre son créateur comme user pour l'ajout
    if for_user is None:
        for_user = interaction.user
        if isinstance(interaction.channel, discord.Thread):
            thread_owner = interaction.channel.owner
            if thread_owner:
                for_user = thread_owner
    print(f"Ajout d'un perso à {for_user.display_name} par {interaction.user.display_name}")
    user_id = str(for_user.id)
    
    ##Gestion du lien de la Fiche##
    if fiche is None:
        messages = [msg async for msg in interaction.channel.history(limit=5)]
        # Trouver le message immédiatement avant la commande
        for msg in messages:
            if msg.id < interaction.id and msg.author != bot.user:
                fiche = msg.jump_url
                break
    #Fail-safe juste au cas ou
    if fiche is None:
        await interaction.followup.send("Impossible de trouver le lien vers la fiche automatiquement.", ephemeral=True)
        return
    
    stats.setdefault(user_id, {}).setdefault("perso", {})

    ##Vérification du Perso à ajouter pour le User##
    perso = {
        "sexe": sexe,
        "orientation": orientation,
        "role": role.lower(),
        "fiche": fiche if fiche else ""
    }
    
    persos = stats.get(user_id, {}).get("perso", {})

    #Vérification de doublon au cas. Peut-être le rechanger en un seul bloc d'objet...?
    if nom in stats[user_id]["perso"]:
        await message(interaction, f"Ce nom de personnage est déjà utilisé.")
        return

    stats[user_id]["perso"][nom] = perso
    
    '''##Gestion des rôles##
    add_role_id = ROLE_MAPPING.get(role)
    add_role = interaction.guild.get_role(add_role_id)
    #print("role a ajouter: " + add_role.name)
    role_multi_id = ROLE_MAPPING.get("Multi")
    discord_role_multi = interaction.guild.get_role(role_multi_id)
    # Vérifie les rôles déjà assignés
    roles_ids = set(ROLE_MAPPING.values())
    roles_actuels_ids = set(role.id for role in for_user.roles)

    # Est-ce que le user a déjà un rôle de perso ?
    a_deja_autre_role = any(role_id in roles_actuels_ids for role_id in roles_ids)

    # Est-ce qu'il a déjà le rôle qu'on veut lui ajouter ?
    a_deja_ce_role = add_role_id in roles_actuels_ids

    # Est-ce qu'il a déjà le rôle multi ?
    a_deja_multi = discord_role_multi.id in roles_actuels_ids'''
    ##Debug
    a_deja_ce_role = True
    
    if not a_deja_ce_role:
        try:
            await for_user.add_roles(add_role, reason="Validation du perso via commande")
            if a_deja_autre_role and not a_deja_multi:
                await for_user.add_roles(discord_role_multi, reason="Validation du perso via commande")
        except discord.Forbidden: #Devrait pas arriver
            await message(interaction, "❌ Je n'ai pas la permission de donner ce rôle.")
        except Exception as e:
            print(f"⚠️ Une erreur est survenue pour l'ajout de {nom} : {e}")
            
    ##Finalisation avec save le fichier et message de validation##
    save_json(stats, interaction.guild.id)
    
    mess_Sex = f"mr. **{nom}**"
    if sexe == "Femme":
        mess_Sex = f"mme. **{nom}**"
    mess_Valid = (f"✅ Félicitations {mess_Sex}, votre inscription a été __*approuvée*__ par la direction.\n"
                  "Nous espérons que votre scolarité à la Ero Academia favorisera l’épanouissement de vos pouvoirs… et de votre sexualité.")#assigner à **{for_user.display_name}**."
    if role == 'Personnel':
        mess_Valid = (f"✅ Félicitations {mess_Sex}, après entretien, la direction a décidé de vous __*embaucher*__.\n"
                    "Bienvenue parmi le personnel. Nous comptons sur vous pour veiller sur la prochaine génération de héro.")
    elif role == 'Autre':
        mess_Valid = (f"✅ Félicitations {mess_Sex}, tout est __*en ordre*__. Voici vos papiers.\n"
                    "Profitez pleinement de tout ce qu’il a à offrir en terme de divertisement et 'détente'.")
    
    await message(interaction, mess_Valid)

@bot.tree.command(name="fouet", description="Temp de faire le ménage.")
@app_commands.guilds(
    discord.Object(id=666059235070574593),  # ID de ton serveur 1
    discord.Object(id=1362186859819565266)   # ID de ton serveur 2
)
# @app_commands.describe(
    # perso=" du personnage",
    # user="Temp de faire le ménage"
# )
async def clean_update(interaction: discord.Interaction):

    stats = load_json(interaction.guild.id)
        
    #Save du fichier juste au cas (Mettre dnas une fonction a part?)
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Ex: 2025-05-25 14:53:00
    fichier = f"Stat-{interaction.guild.id}-Backup-{now}.json"
    with open(f"Stats/{fichier}", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)    
        
    print(f"Demande de nétoyage par {interaction.user.display_name}")

    if not await verif_droit(interaction, stats, "clean"):
        return
    
    nb_clean = 0
    
    for user_id in stats:
        if interaction.guild.get_member(int(user_id)) is None and stats[user_id]["perso"]:
            print(f"Le user {user_id} n'est plus avec nous, suppression de ses perso")
            nb_clean += 1        
            stats[user_id]["perso"] = {}
            stats[user_id]["revenant"] = stats[user_id].get("revenant", 0) + 1
    
    if nb_clean > 0:
        mess = f"J'ai dut donner des coups de fou... Mettre au déchicteur {nb_clean} dossier d{'e' if nb_clean > 1 else '\'une'} personne{'s qui sont' if nb_clean > 1 else ' qui est'} partis de serveur."
    else:
        mess = "Aucune personne ne semble avoir quitter notre beau serveur! <3"
        
    await message(interaction, mess)

    ##Edit du message d'information des stat du serveur   
    #message_id = 1363638934164213791  # L’ID du message à éditer
    message_id = int(1376356880271671369)  # Debug
    #channel = bot.get_channel(842239972864950273)  # L’ID du salon où le message a été posté
    channel = bot.get_channel(1376353412832301137)  # Debug
    message_stats = message_stat_serveur(interaction, stats)
    
    try:
        edit_post = await channel.fetch_message(message_id)
        await edit_post.edit(content=message_stats)
        print("Message de stat du serveur Édité")
    except discord.NotFound:
        # Si le message n'existe plus ou pas, on en crée un nouveau
        print(f"⚠️ Message (id:{message_id}) introuvable, création d’un nouveau.")
        await channel.send(message_stats)
    except Exception as e:
        print(f"❌ Une autre erreur est survenue : {type(e).__name__} - {e}")
    
    save_json(stats, interaction.guild.id)

@bot.tree.command(name="liste", description="Liste des personnages.")
@app_commands.guilds(
    discord.Object(id=666059235070574593),  # ID de ton serveur 1
    discord.Object(id=1362186859819565266)   # ID de ton serveur 2
)
@app_commands.describe(
    fiche="Avec le lien vers la fiche des persos ou sans.",
    user="À qui tu veux voir les persos si pas toi.'"
)
async def liste_persos(
    interaction: discord.Interaction,
    fiche : Literal["Avec", "Sans"] = "Avec",
    user: Optional[discord.Member] = None
):
    print(f"{interaction.user.display_name} sort une liste de perso.")
    await interaction.response.defer()  # Signale que la commande est en traitement
    #await interaction.response.send_message("teste") 

    for_user = user or interaction.user
    user_id = str(for_user.id)
    stats = load_json(interaction.guild.id)
    
    persos = stats.setdefault(user_id, {}).setdefault("perso", {})
    #Un petit trie
    ordre_roles = {
        "élève": 0,
        "personnel": 1,
        "autre": 2
    }
    persos = dict(sorted(
        persos.items(),
        key=lambda item: ordre_roles.get(item[1].get("role", "autre"), 3)  # Valeur par défaut : "autre"
    ))
    
    print(f"voyon voir ce qui a de sortit pour {user_id} - {persos}")
    if persos:
        pages = page_perso(persos, for_user, fiche)
        print(f"Nombre de pages créées : {len(pages)}")

        await interaction.followup.send(
            embed = pages[0],
            view = PaginationView(pages, for_user)  # ou peu importe le nom de ta classe de pagination
        )
    else:
        await message(interaction, f"Aucun personnage trouvé.")

@bot.tree.command(name="stats", description="Donne ses statistique.")
@app_commands.guilds(
    discord.Object(id=666059235070574593),  # ID de ton serveur 1
    discord.Object(id=1362186859819565266)   # ID de ton serveur 2
)
@app_commands.describe(
    user="À qui tu veux voir les stat's"
)
async def stats_persos(
    interaction: discord.Interaction,
    user: Optional[discord.Member] = None
):
    print(f"{interaction.user.display_name} sort des stat de perso.")
    await interaction.response.defer()  # Signale que la commande est en traitement
    ##
    for_user = user or interaction.user
    user_id = str(for_user.id)
    stat_nb_perso = 0
    stats_perso = {
        "sexe": defaultdict(int),
        "orientation": defaultdict(lambda: defaultdict(int)),
        "role": defaultdict(int)
    }

    txt_sexe = ""
    txt_orientation = ""
    
    stats_perso = get_stats(interaction, user_id, stats_perso)
    
    #affiche les stat
    for sexe, nb in stats_perso["sexe"].items():
        stat_nb_perso += nb
        txt_sexe += f"{nb} {sexe}\n"
        for orientation, ori_nb in stats_perso["orientation"].get(sexe).items():
            txt_orientation += f"{ori_nb} {sexe} attirés par {orientation}\n"
    
    text = f"**{for_user.display_name}** possède: {stat_nb_perso} personnages dont\n"+ txt_sexe + txt_orientation +"\n"
    
    for role, nb in stats_perso["role"].items():
        text += f"{nb} {role}\n"
        
    await message(interaction, text)
    
#
####Intéraction####
#

#Perver up
@bot.tree.command(name="pelotte", description="Pelotter l'archiviste")
async def action_pelotte(interaction: discord.Interaction):
    await message(interaction, f"**Se fait pelloter par {interaction.user.display_name}**")
    await message(interaction, f"<:MatsumiSuperShy:1119386825644068945>")

#Cute up
@bot.tree.command(name="calin", description="Calîner l'archiviste")
async def action_calin(interaction: discord.Interaction):
    await message(interaction, f"**Se fait calîner par {interaction.user.display_name}**")
    await message(interaction, f"<:MidnaSmile:1103736201061613658>")
       
#
####Utilité####
#

#Pour pas  avoir a réécrire se long bout de code juste pour un message       
async def message(interaction: discord.Interaction, content: str):
    try:
        await interaction.response.send_message(content)
        return await interaction.original_response()
    except discord.errors.InteractionResponded:
        return await interaction.followup.send(content, wait=True)

def load_json(guild_id: int) -> dict:
    global user_stats
    stats = user_stats.setdefault(guild_id, {})
    fichier = f"Stats/Stat-{guild_id}.json"
    
    try:
        with open(f"{fichier}", "r", encoding="utf-8") as f:
            stats.clear()
            stats.update(json.load(f))
            if user_stats is None:
                print("Fichier JSON vide, initialisation d'un dictionnaire vide.")
                stats = {}
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print("Erreur lors du chargement de Stat.json : {e}. Reset ou Création du fichier")
        stats = {}    

    return stats

def save_json(stats, guild_id: int):
    fichier = f"Stats/Stat-{guild_id}.json"

    with open(f"{fichier}", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

async def verif_droit(interaction, stats, action):
    print(stats.get(str(interaction.user.id), {}).get("droit", {}))
    if  not stats.get(str(interaction.user.id), {}).get("droit", {}).get(action, False):
        if action == "add": action_mess = "d'ajouté un personnage à un autre"
        if action == "clean": action_mess = "de faire le ménage des fiches. J'apprécie ton aide mais il me faut un papier officiel avant"
        if action == "token": action_mess = "de jouer avec les token"
        await message(interaction, f"Euh... excuse-moi mais tu n'as pas le droit {action_mess}... Merci. Je vais devoir le mentioné à <@169586520989106176> <:MidnaShy:1103739968104443954>")
        return False
    return True

def message_stat_serveur(interaction, stats_json): 
    stat_nb_perso = 0
    stats_perso = {
        "sexe": defaultdict(int),
        "orientation": defaultdict(lambda: defaultdict(int)),
        "role": defaultdict(int)
    }

    txt_sexe = ""
    txt_orientation = ""
    #stats_json = load_json(interaction.guild.id)
    for user in stats_json:
        user_id = str(user)
        stats_perso = get_stats(interaction, user_id, stats_perso)
    
    #affichage des stats
    for sexe, nb in stats_perso["sexe"].items():
        stat_nb_perso += nb
        txt_sexe += f"{nb} {sexe}\n"
        for orientation, ori_nb in stats_perso["orientation"].get(sexe).items():
            txt_orientation += f"{ori_nb} **{sexe}{'s' if ori_nb > 1 else ''}** {'est' if ori_nb == 1 else 'sont'} attiré{'e' if sexe == 'femme' else ''}s par les **{orientation if orientation != 'tout' else 'deux'}**\n"
    
    text = f"Il y a {stat_nb_perso} personnes dans la Ero dont\n\n"+ txt_sexe +"\n"+ txt_orientation +"\n"
    
    for role, nb in stats_perso["role"].items():
        text += f"{nb} sont {'du' if role == 'personnel' else 'des'} **{role if role != 'autre' else 'habitant(e)'}s** {'de la Ero' if role != 'élève' else ''}\n"
        
    return text

def get_stats(interaction, user_id, stats_perso):
    #print(f"Calcule des stat de {user_id}")
    stats = load_json(interaction.guild.id)
    
    persos = stats.setdefault(user_id, {}).setdefault("perso", {})
    #print(f"persos de {user_id} : {persos} depuis le fichier {stats}")
    #Fait les stat
    for infos in persos.values():
        sexe = infos.get("sexe", "inconnu")
        orientation = infos.get("orientation", "inconnu")
        
        stats_perso["sexe"][sexe] += 1
        stats_perso["orientation"][sexe][orientation] += 1
        stats_perso["role"][infos.get("role", "autre")] += 1
        #orientation_stats[sexe][orientation] += 1
    #print(f"Information calculer : {stats_perso}")
    return stats_perso

@bot.tree.command(name="nuke", description="T'es sur que tu veux faire ça?")
async def delete_all(interaction: discord.Interaction):
    await interaction.response.defer()  
    
    if interaction.user.id != 169586520989106176:
        await message(interaction, f"Kyaaa! <@169586520989106176> ! <@{interaction.user.id}> essai de détruire les archives! Quelqu'un empêcher le!! <:TienzuPanic:1291506840823136256>")
        return
    print("Début de la Mise à zéro du fichier d'archive")
    
    confirm_msg = await message(interaction,
        f"⚠️ <@{interaction.user.id}> tu es sur le point d'effacer **TOUTES** les données. Clique sur 💥 dans les 10 secondes pour confirmer."
    )
    await confirm_msg.add_reaction("💥")

    def check(reaction, user):
        return (
            user == interaction.user
            and str(reaction.emoji) == "💥"
            and reaction.message.id == confirm_msg.id
        )
        
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=10.0, check=check)
    except asyncio.TimeoutError:
        await confirm_msg.edit(content="⏳ Temps écoulé. Destruction annulée.")
        return
    
    global user_stats
    stats = load_json(interaction.guild.id)
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Ex: 2025-05-25 14:53:00

    fichier = f"Stat-{interaction.guild.id}-Backup-{now}.json"
    with open(f"Stats/{fichier}", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)    
    
    save_json({}, interaction.guild.id)

    stats = {}

@bot.tree.command(name="logout", description="Donner congé à l'archiviste.")
async def logout(interaction: discord.Interaction):
    if interaction.user.id != 169586520989106176:
        await message(interaction, "J'ai-j'ai encore du travaille à faire. Je ne partirai pas tout de suite... <:RozaHigh:1103796416373080084>")
        return
    await message(interaction, "Merci pour ton travaille. À la prochaine.")
    await bot.close()  # Cette méthode ferme proprement le bot

#
####Pagination####
#
def page_perso(persos_dict: dict, for_user: discord.user = None, with_fiche: str = "Avec") -> list:
    pages = []
    persos = list(persos_dict.items())
    print(f"Vérif des perso une fois dans la pagination : {persos}")
    per_page = 10

    for i in range(0, len(persos), per_page):
        bloc = persos[i:i + per_page]
        print(f"Bloc de personnages : {bloc}")  # Vérifie que chaque bloc est bien rempli

        embed = discord.Embed(title= f"📜 **{for_user.display_name}** possède les personnages suivants :", color=discord.Color.blue())

        for nom, infos in bloc:
            sexe = infos.get('sexe', 'asexué')
            role = infos.get('role', 'autre')
            orientation = infos.get('orientation', 'par rien')
            fiche = infos.get('fiche', '')
            
            role_text = (
                "élève" if role == "élève" else
                "membre du personnel" if role == "personnel" else
                f"habitant{'e' if sexe == 'femme' else ''} de la Ero"
            )
            print(f"Perso ajouter a un bloc {nom} {sexe} {role} {orientation} {fiche}")
            embed.add_field(name = "", value =
                f"- Un{'e' if sexe == 'femme' else ''} "
                f"**{role_text}** "
                f"nommé **{nom}** qui est attiré **{orientation}**. "
                f"{fiche if with_fiche == 'Avec' and fiche else ''}",
                inline = False
            )
            
        pages.append(embed)
    return pages
    
class PaginationView(View):
    def __init__(self, pages: list[discord.Embed], user: discord.User):
        super().__init__(timeout=60)
        self.pages = pages
        self.current = 0
        self.user = user
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        print(f"Page actuelle : {self.current}, Total de pages : {len(self.pages)}")

        if self.current > 0:
            button_prev = Button(label="◀️", style=discord.ButtonStyle.secondary)

            async def prev_callback(interaction: discord.Interaction):
                self.current -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.pages[self.current], view=self)

            button_prev.callback = prev_callback
            self.add_item(button_prev)

        if self.current < len(self.pages) - 1:
            button_next = Button(label="▶️", style=discord.ButtonStyle.secondary)

            async def next_callback(interaction: discord.Interaction):
                self.current += 1
                self.update_buttons()
                await interaction.response.edit_message(embed=self.pages[self.current], view=self)

            button_next.callback = next_callback
            self.add_item(button_next)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await message(
                self,
                f"C'est {self.user.display_name} qui a demandé la liste, laisse-le regarder à son rythme s'il te plaît {interaction.user.display_name}.",
                ephemeral=True
            )
            return False
        return True

# Remplace TON_TOKEN_ICI par ton token (garde-le secret !)
bot.run(TOKEN)