from iqoptionapi.stable_api import IQ_Option
from datetime import datetime
import time
import threading
import os, getpass, sys
import logging
import requests

#same as bot8.py
event = threading.Event()
contar_sequencias = threading.Event()
iniciar_programa = threading.Event()
mg_check = threading.Event()
atualiza_primeiro = threading.Event()
#atualiza_lucro = threading.Event()
atualiza_cores = threading.Event()

lock = threading.Lock() #Rlock ou Lock?
semaphore = threading.Semaphore(12)
semaphore2 = threading.Semaphore()
lock2 = threading.RLock()

#PUXANDO EMAIL E SENHA DE ALGUM TXT
if os.stat("user.txt").st_size == 0:
	email = input("Digite seu E-MAIL da IQ Option: ")
	senha = getpass.getpass("Digite sua SENHA da IQ Option: ")
	conta = input("Conta real ou demo: ")
	if conta == "real":
		conta1 = "REAL"
	else:
		conta1 = "PRACTICE"

	login = open('user.txt','w')
	login.write(email)
	login.write("\n")
	
	login.write(senha)
	login.write("\n")
	
	login.write(conta1)
	login.write("\n")
	login.close()
	
else:
	login = open('user.txt','r')
	signin = ["", "", ""]
	for i, linha in enumerate(login):
		linha = linha.rstrip()
		signin[i] = linha
	login.close()
	email = signin[0]
	senha = signin[1]
	conta = signin[2]
	
	if conta == "real":
		conta1 = "REAL"
	else:
		conta1 = "PRACTICE"

#LENDO DADOS DO CANAL DO TELEGRAM ONDE UM BOT POSTARÁ OS RESULTADOS
tlgm = open("telegram.txt", "r")
telegram = ["", ""]
for i, linha in enumerate(tlgm):
	linha = linha.rstrip()
	telegram[i] = linha
tlgm.close()
bot_token = telegram[0]
bot_chatID = telegram[1]

#BOT

def telegram_bot_sendtext(bot_message):
    
    global bot_token, bot_chatID

    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()

stop_gain = 50
stop_loss = 61
quantidade_velas = 15
valor_entrada = 20
martingale = 1
estrategia = 3 #4 = 6x4, 3 = 7x3, 2 = 8x2, etc...

interruptor = 0


API = IQ_Option(email, senha)
API.connect()

API.change_balance(conta1) # PRACTICE / REAL

if API.check_connect():
	print(' Conectado com sucesso!')
else:
	print(' Erro ao conectar')
	input('\n\n Aperte enter para sair')
	sys.exit()

print('''
	     Inicializando Robô...
 ------------------------------------
''')

par_tipo = {}

all_asset = API.get_all_open_time()
for type_name, data in all_asset.items():
    for Asset,value in data.items():
    	if (type_name == "turbo" or type_name == "digital") and (value["open"] == True):
    		if type_name == "turbo":
    			#print("PAR:",Asset,"Binário")
    			par_tipo[Asset] = 2

wins = 0
losses = 0
lucro = 0
'''
def atualizar_lucro(novo_lucro):
	atualiza_lucro.wait()
	lucro = novo_lucro
	atualiza_lucro.clear()
'''

def stop(gain, loss, valor, par, gales):
	global wins, losses, lucro, semaphore2, interruptor
	with semaphore2:
		lucro += valor
		#print("Chegou na função stop mas não passou de wait.")
		event.wait()
		#print("Chegou na função stop e passou de wait.")
		if gales == 0:
			gales = "Sem Gale"
		event.clear()
		if valor > 0:
			wins = wins + 1
			print("WIN em",par,"/",round(valor,2),"/",round(lucro, 2))
			#print("WIN:",wins,"x LOSS",losses)
			winmessage = "Win em " + par + " - Gale: " + str(gales) + "\n\tWIN " + str(wins) + " x LOSS " + str(losses) + "\nSaldo: R$ " + str(round(lucro, 2))
			telegram_bot_sendtext(winmessage)
		elif valor < 0:
			losses = losses + 1
			print("LOSS em",par,"/",round(valor,2),"/",round(lucro, 2), end='')
			#print(" => Martingale:",(mg-2)*-1)
			#if mg == 2:
			#	losses = losses + 1
				#print("WIN:",wins,"x LOSS",losses)
			lossmessage = "Loss em " + par + " - Gale: " + str(gales) + "\n\tWIN " + str(wins) + " x LOSS " + str(losses) + "\nSaldo: R$ " + str(round(lucro, 2))
			telegram_bot_sendtext(lossmessage)
		else:
			print("Empate em",par,"!")
			drawmessage = "Empate em " + par + " - Gale: " + str(gales) + "\n\tWIN " + str(wins) + " x LOSS " + str(losses) + "\nSaldo: R$" + str(round(lucro, 2))
			telegram_bot_sendtext(drawmessage)

		#telegram = 

		gales = 0

		print("\n\nWIN",wins,"x LOSS",losses)

		if lucro <= float('-' + str(abs(loss))):
			print('Stop Loss batido!')
			interruptor = 1
			telegram_bot_sendtext("Stop LOSS batido!\nPrograma finalizado.")
			#input("\nAperte <enter> para finalizar.\n")
			sys.exit()
			
		if lucro >= float(abs(gain)):
			print('Stop Gain Batido!')
			interruptor = 1
			telegram_bot_sendtext("Stop GAIN (win) batido!\nPrograma finalizado.")
			#input("\nAperte <enter> para finalizar.\n")
			sys.exit()

# par, tipo, stop_gain, stop_loss, quantidade_velas, valor_entrada, lucro
os.system('cls' if os.name=='nt' else 'clear')
print("\t\t$ Robô Probabilístico Ativado $\nPares abertos:")
for k in par_tipo:
	print(k)
print("Procurando entrada...")

#def ultimo_ciclo():

def realizar_entrada(par, valor_entrada, direcao, operacao):
	global lock2
	#time.sleep(0.01)
	#lock2.acquire()
	valor = 0
	try:
		lock2.acquire()
		status,id = API.buy_digital_spot(par, valor_entrada, direcao, 1) if operacao == 1 else API.buy(valor_entrada, par, direcao, 1)
		lock2.release()
	except Exception as e:
		telegram_bot_sendtext("Não consegui entrar em " + par)
	
	if status:
		while True:
			#time.sleep(0.01)
			#lock.acquire()
			try:
				status,valor = API.check_win_digital_v2(id) if operacao == 1 else API.check_win_v3(id)
			except:
				status = True
				valor = 0
			#lock.release()

			if status:
				if operacao == 1:
					valor += API.check_win_digital_v2(id)
					print("Resultado em",par,"=",valor)
					break
				else:
					valor += API.check_win_v3(id)
					print("Resultado em",par,"=",valor)
					break
	#lock2.release()

	return valor


#lock2 = threading.RLock()

def puxa_sequencia(quantidade_velas, par, lock, cores):
	#quantidade_velas = quantidade_vela
	contar_sequencias.set()
	#print("cores do par",par,":",cores)
	while True:

		lock.acquire()
		velas = API.get_candles(par, 60, quantidade_velas+1, time.time()) #900 segundos = 15 minutos, 10 = 10 velas
		lock.release()

		cores=""
	
		for i in range(quantidade_velas+1):
			#print(i)
			velas[i] = 'g' if velas[i]['open'] < velas[i]['close'] else 'r' if velas[i]['open'] > velas[i]['close'] else 'd'
			cores += velas[i]

		cores_fatiado = (cores[0:quantidade_velas])
		
		
		contar_sequencias.wait()
		lock.acquire()
		azul = cores_fatiado.count("rggg") + cores_fatiado.count("grrr") #rggg - gggr, grrr - rrrg
		rosa = cores_fatiado.count("rggr") + cores_fatiado.count("grrg") #rggr - rggr, grrg - grrg
		lock.release()
		contar_sequencias.clear()
		contar_sequencias.set()

		#print(par, "stucked in here0") 
		
		if (azul+rosa) < 10:
			#print("\nSó foram encontrados",azul+rosa,"ciclos, adicionando mais 1 velas para catalogação!")
			quantidade_velas = quantidade_velas + 1
			#lock.acquire()
			#velas = API.get_candles(par, 60, quantidade_velas+1, time.time()) #900 segundos = 15 minutos, 10 = 10 velas
		
			#atualiza_cores.set()
			#lock.release()
			continue
		elif (azul+rosa) > 10:
			#print("Pegando as 10 últimas velas...")
			quantidade_velas = 15
			#lock.acquire()
			#velas = API.get_candles(par, 60, quantidade_velas+1, time.time()) #900 segundos = 15 minutos, 10 = 10 velas
		
			#atualiza_cores.set()
			#lock.release()
			continue
		

		#print(par, "stucked in here2")

		encontra_azul = cores_fatiado.find('rggg') 
		#print(encontra_azul,"- rggg")
		encontra_azul2 = cores_fatiado.find('grrr')
		#print(encontra_azul2,"- grrr")
		encontra_rosa = cores_fatiado.find('rggr')
		#print(encontra_rosa,"- rggr")
		encontra_rosa2 = cores_fatiado.find('grrg')
		#print(encontra_rosa2,"- grrg")
		primeiro_azul = -1
		primeiro_rosa = -1
		primeiro_ciclo_a = ""
		primeiro_ciclo_r = ""
		primeiro_ciclo = ""

		if encontra_azul < 0 and encontra_azul2 >= 0:
			primeiro_azul = encontra_azul2
			primeiro_ciclo_a = "grrr"
		elif encontra_azul2 < 0 and encontra_azul >= 0:
			primeiro_azul = encontra_azul
			primeiro_ciclo_a = "rggg"
		elif encontra_azul2 >= 0 and encontra_azul >= 0:
			primeiro_azul = min(encontra_azul, encontra_azul2)
			if encontra_azul < encontra_azul2:
				primeiro_ciclo_a = "rggg"
			else:
				primeiro_ciclo_a = "grrr"

		if encontra_rosa < 0 and encontra_rosa2 >= 0:
			primeiro_rosa = encontra_rosa2
			primeiro_ciclo_r = "grrg"
		elif encontra_rosa2 < 0 and encontra_rosa >= 0:
			primeiro_rosa = encontra_rosa
			primeiro_ciclo_r = "rggr"
		elif encontra_rosa2 >= 0 and encontra_rosa >= 0:
			primeiro_rosa = min(encontra_rosa, encontra_rosa2)	
			if encontra_rosa < encontra_rosa2:
				primeiro_ciclo_r = "rggr"
			else:
				primeiro_ciclo_r = "grrg"

		primeira_sequencia=""
		
		#primeiro_rosa = min(encontra_rosa, encontra_rosa2)
		if(primeiro_azul < primeiro_rosa) and (primeiro_azul >= 0):
			primeira_sequencia = "azul"
			#print("A:",primeiro_ciclo_a)
			primeiro_ciclo = primeiro_ciclo_a
			#print("fechando")
			break
			#print("Primeira sequencia foi azul")
		elif(primeiro_azul > primeiro_rosa) and (primeiro_rosa >= 0):
			primeira_sequencia = "rosa"
			#print("R:",primeiro_ciclo_r)
			primeiro_ciclo = primeiro_ciclo_r
			#print("fechando")
			break
			#print("Primeira sequencia foi rosa")
		elif primeiro_rosa == -1 and primeiro_azul != -1:
			primeira_sequencia = "azul"
			#print("A:",primeiro_ciclo_a)
			primeiro_ciclo = primeiro_ciclo_a
			#print("fechando")
			break
		elif primeiro_azul == -1 and primeiro_rosa != -1:
			primeira_sequencia = "rosa"
			#print("R:",primeiro_ciclo_r)
			primeiro_ciclo = primeiro_ciclo_r
			#print("fechando")
			break
		else:
			primeira_sequencia=""
			primeiro_ciclo = ""
			print("Não foram encontradas sequências, em",par,"...")
			break
	contar_sequencias.clear()
	#print("Em",par,"\nPrimeira sequência:",primeira_sequencia,"\nA:",azul,"x R:",rosa,"\n")

	return primeira_sequencia, azul, rosa, cores_fatiado, primeiro_ciclo

#def ultima_sequencia()

def Martingale(mg, mult, entrada, ciclo, par, op, lock, cores, f_s, primeiro_ciclo):#, lock):
	#print("\n- Buscando oportunidade para martingale no par",par,"\n")
	global lock2, semaphore2
	with semaphore2:
		mg_check.wait()
		mg_check.clear()
		#print("Passou da checagem...")
		gales = 1
		entr = entrada
		#saldo = entrada * -1
		print("Sequencia1:",cores)
		valor = 0
		pos = cores.find(primeiro_ciclo) + 1 #ok!!!!!!!
		#print("full:",cores)
		cores = cores[pos:]
		print("Sequencia1corte:",cores) #show

		ls = ("grrr", "rggg", "grrg", "rggr")

		novo_primeiro = ""
		for i in range(len(ls)):
			if ls[i] in cores and i == 0:
				novo_primeiro = ls[i]
			elif i > 0 and ls[i] in cores:
				if cores.find(ls[i]) < cores.find(novo_primeiro):
					novo_primeiro = ls[i]

		pos = cores.find(novo_primeiro) + 1 #antes do if. OK!
		
		if novo_primeiro == "grrr" or novo_primeiro == "rggg":
			novo_primeiro = "azul"
		elif novo_primeiro == "grrg" or novo_primeiro == "rggr":
			novo_primeiro = "rosa" 

		print(novo_primeiro)

		
		cores = cores[pos:]
		print("Sequencia corte antes do while:",cores)
		result = -1
		while True:
			#print("Verificando se ainda pode fazer gale ou deu win em alguma operação.")
			if gales > mg or result >= 0: #caso valor >= 0, significa que para no Doji (resultado = 0)
				print("gales:",(gales-3)*-1,"valor:",valor)
				break

			

			lock.acquire() #talvez sim talvez nao
			velas_gale = API.get_candles(par, 60, 3, time.time())
			lock.release()

			cores_gale=""
			
			for i in range(3):
				velas_gale[i] = 'g' if velas_gale[i]['open'] < velas_gale[i]['close'] else 'r' if velas_gale[i]['open'] > velas_gale[i]['close'] else 'd'
				cores_gale += velas_gale[i]

			seconds = float(((datetime.now()).strftime('%S'))[:])

			timing = True if seconds >= 58 and seconds <= 59 else False

			if (timing == True) and (cores_gale == "rgg" or cores_gale == "grr") and (ciclo != novo_primeiro):
				print("Martingale =>",gales,":",par)
				if ((ciclo == "azul") and (cores_gale == "rgg")) or ((ciclo == "rosa") and (cores_gale == "grr")): #call
					#lock2.acquire() - Testando. Descomentar em caso de erro
					telegram_bot_sendtext("Realizando Gale " + str(gales) + " em " + par)
					result = realizar_entrada(par, entr*mult*gales, "call", op)
					#lock2.release()
					resultg = str(gales)
					resultgv = str(result)
					telegram_bot_sendtext("Resultado do Gale " + resultg + " em " + par + ": " + resultgv)
					valor = valor + result
					#saldo = saldo + valor
					gales = gales + 1

					for i in range(len(ls)):
						if ls[i] in cores and i == 0:
							novo_primeiro = ls[i]
						elif i > 0 and ls[i] in cores:
							if cores.find(ls[i]) < cores.find(novo_primeiro):
								novo_primeiro = ls[i]

					pos = cores.find(novo_primeiro) + 1
		
					if novo_primeiro == "grrr" or novo_primeiro == "rggg":
						novo_primeiro = "azul"
					elif novo_primeiro == "grrg" or novo_primeiro == "rggr":
						novo_primeiro = "rosa" 

					

					cores = cores[pos:]
					print("Sequencia depois de dar um call:",cores)

				elif ((ciclo == "azul") and (cores_gale == "grr")) or ((ciclo == "rosa") and (cores_gale == "rgg")): #put
					#lock2.acquire() - Testando. Descomentar em caso de erro
					telegram_bot_sendtext("Realizando Gale " + str(gales) + " em " + par)
					result = realizar_entrada(par, entr*mult*gales, "put", op)
					#lock2.release()
					resultg = str(gales)
					resultgv = str(result)
					telegram_bot_sendtext("Resultado do Gale " + resultg + " em " + par + ": " + resultgv)
					valor = valor + result
					#saldo += valor
					gales = gales + 1

					for i in range(len(ls)):
						if ls[i] in cores and i == 0:
							novo_primeiro = ls[i]
						elif i > 0 and ls[i] in cores:
							if cores.find(ls[i]) < cores.find(novo_primeiro):
								novo_primeiro = ls[i]

					pos = cores.find(novo_primeiro) + 1
		
					if novo_primeiro == "grrr" or novo_primeiro == "rggg":
						novo_primeiro = "azul"
					elif novo_primeiro == "grrg" or novo_primeiro == "rggr":
						novo_primeiro = "rosa" 

					print("Ciclo novo:",novo_primeiro)

					

					cores = cores[pos:]

					print("Sequencia depois de dar um put:",cores)

			elif (timing == True) and (cores_gale == "rgg" or cores_gale == "grr") and (ciclo == novo_primeiro):
				print("\nPrimeiro ciclo precisa ser atualizado...\n")
				
				for i in range(len(ls)):
					if ls[i] in cores and i == 0:
						novo_primeiro = ls[i]
					elif i > 0 and ls[i] in cores:
						if cores.find(ls[i]) < cores.find(novo_primeiro):
							novo_primeiro = ls[i]

				pos = cores.find(novo_primeiro) + 1
		
				if novo_primeiro == "grrr" or novo_primeiro == "rggg":
					novo_primeiro = "azul"
				elif novo_primeiro == "grrg" or novo_primeiro == "rggr":
					novo_primeiro = "rosa" 

				print("Novo ciclo:",novo_primeiro)
				

				cores = cores[pos:]
				print("Sequencia depois de ser a primeira=entrada:",cores)
				time.sleep(2)

		saldo = valor - entrada
	return saldo, gales-1

def aposta_azul(azul, rosa, primeira_sequencia, par, stop_gain, stop_loss, quantidade_velas, valor_entrada, martingale, operacao, lock, cores, primeiro_ciclo):
	print("\n\n* Possível entrada em",par,"a favor do ciclo azul, encontrada...\n\n")
	gales = 0
	aposta = "azul"
	global lock2
	while True:
		lock.acquire()
		if interruptor == 1:
			telegram_bot_sendtext("Stop batido, fechando " + par)
			sys.exit()
		lock.release()
		
		lock.acquire()
		proximas_velas = API.get_candles(par, 60, 2+1, time.time())
		lock.release()
		
		proximas_cores=""
		
		for i in range(3): #2+1
			#print("Valor do indice:",i)
			proximas_velas[i] = 'g' if proximas_velas[i]['open'] < proximas_velas[i]['close'] else 'r' if proximas_velas[i]['open'] > proximas_velas[i]['close'] else 'd'
			proximas_cores += proximas_velas[i]

		segundos = float(((datetime.now()).strftime('%S'))[:])
		entrar = True if segundos >= 58 and segundos <= 59 else False#>= 58 and segundos <= 59 else False
		
		
		if (entrar == True) and (proximas_cores == "rgg"):
			
			direcao = "call"
			print("--- Entrando em",par,":",aposta.upper(),"---\nCiclos Azuis:",azul,"\nCiclos Rosas:",rosa,"\nPrimeira Sequência:",primeira_sequencia,"\nCiclo:",primeiro_ciclo)
			telegram_bot_sendtext("Realizando entrada em " + par)
			#lock.acquire()
			time.sleep(0.01)
			
			valor = realizar_entrada(par, valor_entrada, direcao, operacao)
			
			lock2.acquire()
			valor_temp = valor
			lock2.release()
				
			
			if valor_temp < 0 and martingale > 0:
				#print("Precisa de gale...")
				telegram_bot_sendtext("A entrada em " + par + " deu loss. Procurando Gale 1.")
				mg_check.set()
				mgr, gales = Martingale(martingale, 2, valor_entrada, aposta, par, operacao, lock, cores, primeira_sequencia, primeiro_ciclo) #2 = multiplicador do gale
				
				
				event.set()
				stop(stop_gain, stop_loss, mgr, par, gales) #stop_gain, stop_loss, valor_temp, martingale, par
				
				break
			else:
				event.set()
				stop(stop_gain, stop_loss, valor_temp, par, 0)
			#lock.release()
			break

		elif (entrar == True) and (proximas_cores == "grr"):
			
			
			direcao = "put"
			print("--- Entrando em",par,":",aposta.upper(),"---\nCiclos Azuis:",azul,"\nCiclos Rosas:",rosa,"\nPrimeira Sequência:",primeira_sequencia,"\nCiclo:",primeiro_ciclo)
			telegram_bot_sendtext("Realizando entrada em " + par)
			#lock.acquire()
			time.sleep(0.01)
			
			valor = realizar_entrada(par, valor_entrada, direcao, operacao)
			
			lock2.acquire()
			valor_temp = valor
			lock2.release()

				
			
			if valor_temp < 0 and martingale > 0:
				#print("Precisa de gale...")
				
				telegram_bot_sendtext("A entrada em " + par + " deu loss. Procurando Gale 1.")
				mg_check.set()
				mgr, gales = Martingale(martingale, 2, valor_entrada, aposta, par, operacao, lock, cores, primeira_sequencia, primeiro_ciclo) #2 = multiplicador do gale
				
				
				event.set()
				stop(stop_gain, stop_loss, mgr, par, gales) #stop_gain, stop_loss, valor_temp, martingale, par
				
				break
			else:
				event.set()
				stop(stop_gain, stop_loss, valor_temp, par, 0)
			#lock.release()
			break
def aposta_rosa(azul, rosa, primeira_sequencia, par, stop_gain, stop_loss, quantidade_velas, valor_entrada, martingale, operacao, lock, cores, primeiro_ciclo):

		
	print("\n\n* Possível entrada em",par,"a favor do ciclo rosa, encontrada...\n\n")
	entr = valor_entrada
	gales = 0
	aposta = "rosa"
	valor_temp = 0
	global lock2
	while True:
		lock.acquire()
		if interruptor == 1:
			telegram_bot_sendtext("Stop batido, fechando " + par)
			sys.exit()
		lock.release()
		
		#time.sleep(0.01)
		lock.acquire()
		proximas_velas = API.get_candles(par, 60, 2+1, time.time())
		lock.release()

		proximas_cores=""

		for i in range(3): #2+1
			proximas_velas[i] = 'g' if proximas_velas[i]['open'] < proximas_velas[i]['close'] else 'r' if proximas_velas[i]['open'] > proximas_velas[i]['close'] else 'd'
			proximas_cores += proximas_velas[i]
		
		segundos = float(((datetime.now()).strftime('%S'))[:])
		entrar = True if segundos >= 58 and segundos <= 59 else False#>= 58 and segundos <= 59 else False
		
		
		if (entrar == True) and (proximas_cores == "rgg"):
			direcao = "put"
			print("--- Entrando em",par,":",aposta.upper(),"---\nCiclos Azuis:",azul,"\nCiclos Rosas:",rosa,"\nPrimeira Sequência:",primeira_sequencia,"\nCiclo:",primeiro_ciclo)
			telegram_bot_sendtext("Realizando entrada em " + par)
			#lock.acquire()
			time.sleep(0.01)
			
			valor = realizar_entrada(par, valor_entrada, direcao, operacao)
			
			lock2.acquire()
			valor_temp = valor
			lock2.release()
			
			if valor_temp < 0 and martingale > 0:
				#print("Precisa de gale...")
				
				telegram_bot_sendtext("A entrada em " + par + " deu loss. Procurando Gale 1.")
				mg_check.set()
				mgr, gales = Martingale(martingale, 2, valor_entrada, aposta, par, operacao, lock, cores, primeira_sequencia, primeiro_ciclo) #2 = multiplicador do gale
				
				event.set()
				stop(stop_gain, stop_loss, mgr, par, gales) #stop_gain, stop_loss, valor_temp, martingale, par
				
				break
			else:
				event.set()
				stop(stop_gain, stop_loss, valor_temp, par, 0)
			#lock.release()
			break

		elif (entrar == True) and (proximas_cores == "grr"):
			direcao = "call"
			print("--- Entrando em",par,":",aposta.upper(),"---\nCiclos Azuis:",azul,"\nCiclos Rosas:",rosa,"\nPrimeira Sequência:",primeira_sequencia,"\nCiclo:",primeiro_ciclo)
			telegram_bot_sendtext("Realizando entrada em " + par)
			#lock.acquire()
			time.sleep(0.01)
			
			valor = realizar_entrada(par, valor_entrada, direcao, operacao)
			
			lock2.acquire()
			valor_temp = valor
			lock2.release()
	
			
			if valor_temp < 0 and martingale > 0:
				#print("Precisa de gale...")
				
				telegram_bot_sendtext("A entrada em " + par + " deu loss. Procurando Gale 1.")
				mg_check.set()
				mgr, gales = Martingale(martingale, 2, valor_entrada, aposta, par, operacao, lock, cores, primeira_sequencia, primeiro_ciclo) #2 = multiplicador do gale
				
				
				event.set()
				stop(stop_gain, stop_loss, mgr, par, gales) #stop_gain, stop_loss, valor_temp, martingale, par
				
				break
			else:
				event.set()
				stop(stop_gain, stop_loss, valor_temp, par, 0)
			#lock.release()
			break

def probabilistico(threadID, par, operacao, lock):
	global stop_gain, stop_loss, quantidade_velas, valor_entrada, martingale, estrategia

	#stop_gain = 50
	#stop_loss = 21
	#quantidade_velas = 15
	#valor_entrada = 2
	#martingale = 2 #2

	#rosa = 0
	#azul = 0
	#primeira_sequencia = "indefinida"

	#logging.debug("Encontrou entrada...")
	#iniciar_programa.set()
	while True:
		aposta = "indefinida."
		#print(current_thread().name)
		
		#print(threadID)
		lock.acquire()
		velas = API.get_candles(par, 60, quantidade_velas+1, time.time()) #900 segundos = 15 minutos, 10 = 10 velas
		lock.release()

		time.sleep(0.1)
		semaphore.acquire()

		cores=""
		
		for i in range(quantidade_velas+1):
			#print(i)
			velas[i] = 'g' if velas[i]['open'] < velas[i]['close'] else 'r' if velas[i]['open'] > velas[i]['close'] else 'd'
			cores += velas[i]
		#print("ok")
		
	
		if cores[quantidade_velas-3:-1] == "grr" or cores[quantidade_velas-3:-1] == "rgg":
			#print("A função foi cancelada em",par,"pois há um ciclo se fechando.")
			semaphore.release()
			continue
		

		#print("aqui")
		try:
			atualiza_cores.set()
			primeira_sequencia, azul, rosa, cores, primeiro_ciclo = puxa_sequencia(quantidade_velas, par, lock, cores)
			#print("par:",par,"ciclos a/r:",azul,"-",rosa,"primeira seq:",primeira_sequencia)
		except Exception as e:
			semaphore.release()
			continue
		#print("aqui2")

		#if cores[quantidade_velas-3:-1] == "grr" or cores[quantidade_velas-3:-1] == "rgg":
			#print("A função foi cancelada em",par,"pois há um ciclo se fechando.")
			#semaphore.release()
			#continue
		
			
			#print(str(e))
			 #Se cair aqui é pq está havendo uma decisão de novo ciclo. Que poderia mudar as sequências
		lock.acquire()
		if interruptor == 1:
			telegram_bot_sendtext("Stop batido, fechando " + par)
			sys.exit()
		lock.release()
		#print(threadID)
		if azul/(azul+rosa) <= estrategia/10 and (azul+rosa) >= 10 and primeira_sequencia == "rosa":
			#print(threadID, "rosa")

			#time.sleep(0.01)
			#lock.acquire()
			
			aposta_azul(azul, rosa, primeira_sequencia, par, stop_gain, stop_loss, quantidade_velas, valor_entrada, martingale, operacao, lock, cores, primeiro_ciclo)
			#lock.release()
			
		elif rosa/(azul+rosa) <= estrategia/10 and (azul+rosa) >= 10 and primeira_sequencia == "azul":
			#logging.info("Encontrou entrada...")
			#print(threadID, "azul")
			#time.sleep(0.01)
			#lock.acquire()
			#print(current_thread().name)
			#logging.debug("Encontrou entrada...")
			#print(threadID)
			aposta_rosa(azul, rosa, primeira_sequencia, par, stop_gain, stop_loss, quantidade_velas, valor_entrada, martingale, operacao, lock, cores, primeiro_ciclo)
			#lock.release()
		semaphore.release()

threads = list()

#telegram_bot_sendtext("*\nEntrando com a seguinte configuração:\nEntrada: R$ 20\nStop gain: R$ 500\nStop loss (1 hit): R$ 61 (Mas pode ser até 20 + 40 + 80 = 140...)\n2 gales...\nCiclos 8x2\n*\n")
for i, k in enumerate(par_tipo):
	#print("par:",k,"i=",i)
	
	thread = threading.Thread(target=probabilistico, args=(i, k, par_tipo[k],lock))
	threads.append(thread)
	thread.start()

#threadAtt = threading.Thread(, daemon=True)
#threadAtt.start()

telegram_bot_sendtext("$ Robô Iniciado $\nEntrada: R$ " + str(valor_entrada) + "\nStop gain: R$ " + str(stop_gain) + "\nStop loss: R$ " + str(stop_loss) + "\nGales: " + str(martingale) + "\nCiclos: " + str((estrategia-10)*-1) + "x" + str(estrategia))

for t in threads:
    t.join()
