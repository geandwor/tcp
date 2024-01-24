import random
from queue import Queue
from typing import Dict

received: Dict[int, bool] = {}
first_sent: Dict[int,int] = {} 
pkt_buf: Queue(int) = Queue()


# Enqueue a list of elements
pkt_buf.put(1)
tokens = 1
last_pkt_sent = 1
last_ack_sent = 0
last_ack_rcvd = 0
beta = 10 #queue capacity
K = 10 #capacity of TBF
cwnd = 1
state = 0 #SlowStart. Fast Recovery is 1 
num_dup = 0
tau = 0

##set of constants for updating the RTO
init_r :bool = False
MINUNIT = 5
ralpha = 1/8
rbeta = 1/4
rK = 4
rG = MINUNIT
rto = 10

#propagation delay
Rm = 5

random.seed(5)

#STEP
while state == 0:
    tau += 1
    # max number of tokens 
    bound = min(tokens, pkt_buf.qsize())
    # choose a number of tokens to remove. 
    num_tokens = random.randint(0, bound)
    # remove the tokens and add 1 for the next time step, not to exceed K
    tokens = min(tokens - num_tokens + 1,K)
    # prepare packets to be sent to queue; if first transmission, record time
    pkts_sent = []
    for _ in range(num_tokens):
        pkt = pkt_buf.get()
        ##set to tau on first transmission and 0 on retransmits
        if pkt not in first_sent:
            first_sent[pkt] = tau
        else:
            first_sent[pkt] = 0
        pkts_sent.append(pkt)
# Reciver processing incoming packets (in pkts_sent):
# for each packet sent
# set its received value to true
# starting from last_ack + 1, find the first non-received element
# and add the previous one (highest consecutive received) to
#the ack buffer
   
    ack_buf = []
#    print("building new ack buffer")
    while pkts_sent:
        pkt = pkts_sent.pop(0)
        received[pkt] = True
        print(f"received packet {pkt}")
        cur = last_ack_sent + 1
        ##????I believe there is some problem
        while received.get(cur, False):
            cur += 1
        cur -= 1
        ack_buf.append(cur)
        last_ack_sent = cur

#
#Sender processing acks (in ack_buf)
    while ack_buf:
        #remove an ack from ack_buf
        ack = ack_buf.pop(0)
        if ack > last_ack_rcvd:
            # if a new ack, check the pkt[last_ack_rcvd+1: ark) visited once
            ok_to_update: bool = False
            tmp_pkt: int = last_ack_rcvd
            while tmp_pkt < ack:
                if (tmp_pkt+1) in first_sent and first_sent[tmp_pkt+1] > 0:
                    tmp_pkt += 1
            if tmp_pkt == ack:
                ok_to_update = True
    
            ##update RTO when ok_to_calc
            if(ok_to_update):
                rtt = tau - first_sent[last_ack_rcvd + 1] ## fixed: not correct. only if first_sent[last_ack_rcvd + 1..ack] > 0
                if not init_r:
                    srtt = rtt
                    #rttvar = rtt/2
                    init_r = True
                else:
                    #rttvar = (1-rbeta)*rttvar + rbeta*abs(srtt-rtt)
                    srtt = (1-ralpha)*srtt + ralpha*rtt
                rto = srtt + rG ##ignore rttvar now
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
                pkt_buf.put(last_pkt_sent)
#                #time to sent
#                if last_pkt_sent not in first_sent:
#                    first_sent[last_pkt_sent] = tau
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
    
            

