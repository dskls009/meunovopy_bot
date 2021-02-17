import logging
import pycurl
import certifi
from io import BytesIO
from bs4 import BeautifulSoup
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
from dicio import Dicio
from numpy import random
from models import db, Awa_Foto
from google_images_search import GoogleImagesSearch
from variaveis import TOKEN, DEVELOPER_KEY, CX

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
CHAT_E_TITULO ={}
CONTEXTO_BUSCA = None
CHAT_OQ = {}
CHAT_INT = {}
CONTEXTO_BUSCA_JISHO = None
CHAT_OQ_JISHO = {}
CHAT_INT_JISHO = {}
CONTEXTO_BUSCA_IMG = None
CHAT_OQ_IMG = {}
CHAT_INT_IMG = {}
SITE = 'https://jisho.org/api/v1/search/words?'
AGUA = {}

class Bot():

    def start(update: Update, context: CallbackContext) -> None:
        update.message.reply_text('oi chocoleute eu sou um bot em fase de testes\n'
        '/start: lista os comandos do bot\n'
        '/noticia: busca a noticia mais recente do site g1/mundo\n'
        '/youtube [pesquisa]: busca um vídeo no youtube\n'
        '/more: busca o próximo vídeo da busca anterior no youtube, até o vigésimo quinto\n'
        '/jisho [palavra]: busca uma palavra no dicionário japonês-inglês\n'
        '/motto: busca o próximo registro no dicionário\n'
        '/significado [palavra]: busca o significado de uma palavra no dicionário\n'
        '/etimologia [palavra]: busca a etimologia de uma palavra no dicionário\n'
        '/sinonimos [palavra]: busca sinônimos de uma palavra no dicionário\n'
        '/agua: inicia um alarme que manda uma foto de hora em hora no chat\n'
        'para adicionar fotos à lista, basta enviar uma foto respondendo o bot')

    def agua_meme(context:CallbackContext):
        agua = []
        fotos = Awa_Foto.query.filter_by(chat_id=str(context.job.context)).all()
        for foto in fotos:
            agua.append(foto.file_id)
        x = random.randint(len(agua))
        context.bot.send_photo(chat_id=context.job.context, photo=agua[x])

    def add_agua_meme(update:Update, context:CallbackContext):
        for foto in update.message.photo:
            if foto.file_id:
                awa_foto = Awa_Foto(file_id=foto.file_id, chat_id=str(update.effective_chat.id))
                db.session.add(awa_foto)
                db.session.commit()
                break

    def agua(update:Update, context:CallbackContext):
        global AGUA
        if update.effective_chat.id in AGUA:
            fotos = Awa_Foto.query.filter_by(chat_id=str(update.effective_chat.id)).all()
            if len(fotos) == 0:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Lista de memes vazia.")
                return
            if not AGUA.get(update.effective_chat.id):
                AGUA.update({update.effective_chat.id:True})
                context.job_queue.run_repeating(Bot.agua_meme, 36000, 2, context=update.effective_chat.id)
            elif AGUA.get(update.effective_chat.id):
                AGUA.update({update.effective_chat.id:False})
                context.bot.send_message(chat_id=update.effective_chat.id, text="Comando cancelado!")
        else:
            AGUA[update.effective_chat.id] = False
            fotos = Awa_Foto.query.filter_by(chat_id=str(update.effective_chat.id)).all()
            if len(fotos) == 0:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Lista de memes vazia.")
                return
            AGUA.update({update.effective_chat.id:True})
            context.job_queue.run_repeating(Bot.agua_meme, 36000, 2, context=update.effective_chat.id)

class Dicionario():

    def dicio(update:Update, context:CallbackContext):
        dicio = Dicio()
        palavra = dicio.search(context.args[0])
        sinonimos = ''
        if update.message.text[0:12].lower() == "/significado":
            if palavra is None:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Escreveu direitinho? Em português? Porque, olha, não achei nada aqui não...")
                return
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=palavra.meaning)
        elif update.message.text[0:11].lower() == "/etimologia":
            if palavra is None:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Escreveu direitinho? Em português? Porque, olha, não achei nada aqui não...")
                return
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=palavra.etymology)
        elif update.message.text[0:10].lower() == "/sinonimos":
            if palavra is None:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Escreveu direitinho? Em português? Porque, olha, não achei nada aqui não...")
                return
            else:
                for sinonimo in palavra.synonyms:
                    sinonimos = sinonimos+sinonimo.word+', '
                context.bot.send_message(chat_id=update.effective_chat.id, text=sinonimos[:-2])

class JishoOrg():
    
    def jisho(update:Update, context:CallbackContext):
        global CONTEXTO_BUSCA_JISHO
        global CHAT_OQ_JISHO
        global CHAT_INT_JISHO
        if context.args!=[] and update.message.text[0:6].lower() == '/jisho':
            CONTEXTO_BUSCA_JISHO = context.args[0:]
            CHAT_OQ_JISHO[update.effective_chat.id] = CONTEXTO_BUSCA_JISHO
            CHAT_INT_JISHO[update.effective_chat.id] = 0
        elif context.args==[] and update.message.text[0:6].lower() == '/jisho':
            context.bot.send_message(chat_id=update.effective_user.id, text='Digite /jisho e o que deseja pesquisar.')
            return
        elif context.args!=[] and update.message.text[0:6].lower() == '/motto':
            context.bot.send_message(chat_id=update.effective_user.id, text='Não é assim que funciona o /motto.')
            return
        elif context.args==[] and update.message.text[0:6].lower() == '/motto':
            CHAT_INT_JISHO[update.effective_chat.id]+= 1

        context.bot.send_message(chat_id=update.effective_chat.id, text=JishoOrg.busca_jisho(CONTEXTO_BUSCA_JISHO, update))

    def busca_jisho(args, update):
        global CHAT_INT_JISHO
        request = requests.get(SITE, params={'keyword':args})
        json = request.json()
        resultado = ''
        
        if CHAT_INT_JISHO[update.effective_chat.id] == len(json['data']):
            CHAT_INT_JISHO[update.effective_chat.id] = 0
        data = json['data'][CHAT_INT_JISHO.get(update.effective_chat.id)]
        for lista_japanese in data['japanese']:
            if lista_japanese.get('word'):
                resultado=resultado+lista_japanese.get('word')+' '
            resultado=resultado+lista_japanese.get('reading')+' / '
        resultado=resultado[:-3]+'\n'
        for lista_senses in data['senses']:
            for speech in lista_senses.get('parts_of_speech'):
                resultado=resultado+speech+', '
            resultado=resultado[:-2]+'\n=> '
            for english in lista_senses.get('english_definitions'):
                resultado=resultado+english+', '
            resultado=resultado[:-2]+'\n'
        return resultado

class NewsSearch():

    def noticias(update:Update, context:CallbackContext):
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, 'https://g1.globo.com/mundo/')
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.CAINFO, certifi.where())
        c.perform()
        c.close()
        parsed_html = BeautifulSoup(buffer.getvalue(), 'html.parser')
        titulo = parsed_html.find("div", class_="feed-post-body-title").a.string
        link = parsed_html.find("a", class_="feed-post-link").get('href')
        metadata = parsed_html.find("span", class_="feed-post-metadata-section").string
        global CHAT_E_TITULO
        if update.effective_chat.id in CHAT_E_TITULO:
            if CHAT_E_TITULO[update.effective_chat.id] == titulo:
                return
            else:
                CHAT_E_TITULO[update.effective_chat.id] = titulo
        else:
            CHAT_E_TITULO[update.effective_chat.id] = titulo
        
        context.bot.send_message(chat_id=update.effective_chat.id, text=titulo+'\n'+link+'\nCategoria: '+metadata)

class YoutubeSearch():

    def youtube(update:Update, context:CallbackContext):
        global CONTEXTO_BUSCA
        global CHAT_OQ
        global CHAT_INT
        if context.args!=[] and update.message.text[0:8].lower() == '/youtube':
            CONTEXTO_BUSCA = context.args[0:]
            CHAT_OQ[update.effective_chat.id] = CONTEXTO_BUSCA
            CHAT_INT[update.effective_chat.id] = 0
        elif context.args==[] and update.message.text[0:8].lower() == '/youtube':
            context.bot.send_message(chat_id=update.effective_user.id, text='Digite o que deseja pesquisar.')
            return
        elif context.args!=[] and update.message.text[0:5].lower() == '/more':
            context.bot.send_message(chat_id=update.effective_user.id, text='Não é assim que funciona o /more.')
            return
        elif context.args==[] and update.message.text[0:5].lower() == '/more':
            CHAT_INT[update.effective_chat.id]+= 1
        

        parser = argparse.ArgumentParser()
        parser.add_argument('--q', help='Search term', default='')
        parser.add_argument('--max-results', help='Max results', default=25)
        args = parser.parse_args(['--q', '%s' % CHAT_OQ.get(update.effective_chat.id)])
        
        try:
            context.bot.send_message(chat_id=update.effective_chat.id, text=YoutubeSearch.busca_youtube(options=args, update=update))
        except HttpError as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text='An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))

    def busca_youtube(options, update):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY, cache_discovery=False)
        search_response = youtube.search().list(
            q=options.q,
            part='id,snippet',
            maxResults=options.max_results
        ).execute()

        videos = []

        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#video':
                videos.append('%s (https://youtu.be/%s)' % (search_result['snippet']['title'], search_result['id']['videoId']))
        global CHAT_INT
        
        if CHAT_INT[update.effective_chat.id] == 24:
            CHAT_INT[update.effective_chat.id] = 0
        video = videos[CHAT_INT.get(update.effective_chat.id)]
        
        return video

class ImageSearch():
    
    def imagem(update:Update, context:CallbackContext):
        global CONTEXTO_BUSCA_IMG
        global CHAT_OQ_IMG
        global CHAT_INT_IMG
        if context.args!=[] and update.message.text[0:4].lower() == '/img':
            CONTEXTO_BUSCA_IMG = context.args[0:]
            CHAT_OQ_IMG[update.effective_chat.id] = CONTEXTO_BUSCA_IMG
            CHAT_INT_IMG[update.effective_chat.id] = 0
        elif context.args==[] and update.message.text[0:4].lower() == '/img':
            context.bot.send_message(chat_id=update.effective_user.id, text='Digite /img e o que deseja pesquisar.')
            return
        elif context.args!=[] and update.message.text[0:5].lower() == '/next':
            context.bot.send_message(chat_id=update.effective_user.id, text='Não é assim que funciona o /next.')
            return
        elif context.args==[] and update.message.text[0:5].lower() == '/next':
            CHAT_INT_IMG[update.effective_chat.id]+= 1

        parametros_busca = {
            'q': CHAT_OQ_IMG.get(update.effective_chat.id),
            'num': 10,
            'safe': 'off',
        }
        gis = GoogleImagesSearch(DEVELOPER_KEY, CX)

        imagens = []

        gis.search(search_params=parametros_busca)
        for image in gis.results():
            imagens.append(image.url)

        if CHAT_INT_IMG[update.effective_chat.id] == 9:
            CHAT_INT_IMG[update.effective_chat.id] = 0
        imagem = imagens[CHAT_INT_IMG.get(update.effective_chat.id)]

        context.bot.send_photo(chat_id=update.effective_chat.id, photo=imagem)

def main():
    updater = Updater(TOKEN, use_context=True)
    jobqueue = updater.job_queue

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", Bot.start))
    dispatcher.add_handler(CommandHandler("agua", Bot.agua))
    dispatcher.add_handler(CommandHandler("noticia", NewsSearch.noticias))
    dispatcher.add_handler(CommandHandler("youtube", YoutubeSearch.youtube))
    dispatcher.add_handler(CommandHandler("more", YoutubeSearch.youtube))
    dispatcher.add_handler(CommandHandler("jisho", JishoOrg.jisho))
    dispatcher.add_handler(CommandHandler("motto", JishoOrg.jisho))
    dispatcher.add_handler(CommandHandler("significado", Dicionario.dicio))
    dispatcher.add_handler(CommandHandler("etimologia", Dicionario.dicio))
    dispatcher.add_handler(CommandHandler("sinonimos", Dicionario.dicio))
    dispatcher.add_handler(CommandHandler("img", ImageSearch.imagem))
    dispatcher.add_handler(CommandHandler("next", ImageSearch.imagem))

    dispatcher.add_handler(MessageHandler(Filters.photo, Bot.add_agua_meme))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()

