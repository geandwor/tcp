import random
from queue import Queue
from typing import Dict

received: Dict[int, bool] = {}
first_sent: Dict[int,int] = {} 
pkt_buf: Queue((int, int)) = Queue() # queue of tuple(pkt_id, time)


# Enqueue a list of elements
pkt_buf.put((1,0))
last_pkt_sent = 1
last_ack_sent = 0
last_ack_rcvd = 0
beta = 10 #queue capacity
K = 10 #capacity of TBF
cwnd = 1
state = 0 #SlowStart. Fast Recovery is 1 
from typing import List
num_dup = 0
tau = 0

C = 3 #speed for token sending
#keep token length <=D
tokens: List[int] = []
tokens.append(C)
D = 2#time to live for tokens

##set of constants for updating the RTO
init_r :bool = False
srtt = -1
MINUNIT = 4
ralpha = 1/8
rbeta = 1/4
rK = 4
rG = MINUNIT
rto = 2

#propagation delay
Rm = 3
ack_buf = []

random.seed(5)

#remove used token from the tokens buffer
def removeOverFlow(tokens: List[int], num_remove: int) -> None:
    for i in range(len(tokens)):
        if num_remove>0:
            if tokens[i]>0:
                if tokens[i]<=num_remove:
                    num_remove -= tokens[i]
                    tokens[i] = 0
                else:
                    tokens[i] -= num_remove
                    num_remove = 0
        else:
            break
    return

#ok_to_update
def okToUpdate(cur: int, ack: int, first_sent: Dict[int, int]) -> bool:
    ok_to_update = False
    while cur < ack:
        if (cur+1) in first_sent and first_sent[cur+1] >= 0:
            cur += 1
        else:
            break
    if cur == ack:
        ok_to_update = True
    return ok_to_update

#update rto
def updateTripTime(first_sent: Dict[int, int], last_ack: int, cur: int, srtt: float, rG: int, ralpha: float) -> List[int]:
    rtt = cur - first_sent[last_ack_rcvd + 1] ## fixed: not correct. only if first_sent[last_ack_rcvd + 1..ack] > 0
    if srtt<0:
        srtt = rtt
        #rttvar = rtt/2
    else:
        #rttvar = (1-rbeta)*rttvar + rbeta*abs(srtt-rtt)
        srtt = (1-ralpha)*srtt + ralpha*rtt
    rto = srtt + rG ##ignore rttvar now
    return [rtt, rto, srtt]
    

#STEP
while state == 0:
    #print(f"time is {tau}")
    tau += 1
    # max number of tokens 
    if(len(tokens)>D):
        tokens.pop(0)
    
    bound = min(sum(tokens), pkt_buf.qsize())
    # choose a number of tokens to remove. 
    num_tokens = random.randint(0, bound)
    # remove the tokens and add C for the next time step, not to exceed K
    if num_tokens>0:
        removeOverFlow(tokens, num_tokens)
    tokens.append(C)
    #remove token when overflow the token buffer
    if sum(tokens)>K:
       removeOverFlow(tokens, sum(tokens)-K)   
    
    # prepare packets to be sent to queue; if first transmission, record time; otherwise record -1
    pkts_sent = []
    for _ in range(num_tokens):
        pkt, t = pkt_buf.get()
        ##assign t to the first visited packet
        if pkt not in first_sent:
            first_sent[pkt] = t
        else:
            first_sent[pkt] = -1
        pkts_sent.append(pkt)
# Reciver processing incoming packets (in pkts_sent):
# for each packet sent
# set its received value to true
# starting from last_ack + 1, find the first non-received element
# and add the previous one (highest consecutive received) to
#the ack buffer
   
    ack_buf_tau = []
#    print("building new ack buffer")
    while pkts_sent:
        pkt = pkts_sent.pop(0)
        received[pkt] = True
        print(f"received packet {pkt}")
        cur = last_ack_sent + 1
        while received.get(cur, False):
            cur += 1
        cur -= 1
        #to mimic loss of ark
#        ind = random.randint(0,100)%100
#        print(f"indicator is {ind}")
#        if cur==1:
#            ack_buf_tau.append(cur)
#        elif(ind%2==1):
#            ack_buf_tau.append(cur)
        ack_buf_tau.append(cur)
        last_ack_sent = cur
    ack_buf.append(ack_buf_tau)


#Sender processing acks (in ack_buf)
    while len(ack_buf)>Rm:
        #print(f"ack_buf is {ack_buf} first_sent is {first_sent}")
        #remove an ack from ack_buf
        acklist = ack_buf.pop(0)
        while(acklist):
            ack = acklist.pop(0)
            if ack > last_ack_rcvd:
                # if a new ack, check the pkt[last_ack_rcvd+1: ark) visited once
                ok_to_update: bool = okToUpdate(last_ack_rcvd, ack, first_sent)
        
                ##update RTO when ok_to_calc
                if(ok_to_update):
                    rtt, rto, srtt = updateTripTime(first_sent, last_ack_rcvd, tau, srtt, rG, ralpha)
                    print(f"rtt is {rtt} and rto is {rto}")
                    print(f"New RTT sample with ack: {ack} and packet {last_ack_rcvd + 1} current rto is {rto} ")
            
                ## update last_ack
                last_ack_rcvd = ack
                ## indicate it's the first time ack is received
                num_dup = 1
                ## increment cwnd 
                cwnd +=  1
                ## fill in pkt_buf with as many new packets as possible
                ## that is, to fill cwnd w/o overflowing the buffer
                while pkt_buf.qsize() < beta and  (last_pkt_sent - ack) < cwnd:
                    last_pkt_sent += 1
                    pkt_buf.put((last_pkt_sent, tau))
                if last_pkt_sent - ack < cwnd:
                    ### cwnd is larger than buffer's capacity, then pkts are dropped
                    ### suffices to increase last_pkt_sent 
                    last_pkt_sent = cwnd + ack
            else:
                # if a repeat ack then increment num_dup 
                num_dup += 1
    #           print(f"Duplicate number {num_dup} of  {ack}")
            if num_dup == 4:
                # after 4 consecutive acks move to fast recovery 
                state = 1
                print(f"going to fast recovery with cwnd: {cwnd} qsize: {pkt_buf.qsize()} and last ack: {ack}")
        
            

