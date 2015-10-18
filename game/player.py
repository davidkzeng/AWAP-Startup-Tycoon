import networkx as nx
import random
import math
from base_player import BasePlayer
from settings import *

class Player(BasePlayer):
    """
    You will implement this class for the competition. DO NOT change the class
    name or the base class.
    """

    # You can set up static state here
    has_built_station = False
    def __init__(self, state):
        graph = state.get_graph()
        self.numNodes = len(graph.nodes())
        self.shortPath = [None for x in range(self.numNodes)]
        #calcFirst = min(200,self.numNodes)
        #for i in range(calcFirst):
         #   self.shortPath[i] = nx.single_source_dijkstra_path_length(graph, i)
        maxWait = int(10/ORDER_CHANCE)
        self.waitTime = min(40,maxWait)

        self.unreached = []
        self.stations = []
        self.buildCost = INIT_BUILD_COST
        self.lastBuild = 0
        self.timeToDiss = int(math.ceil(SCORE_MEAN / DECAY_FACTOR))
        self.totalProfit = 0
        self.lastStationProfit = 0

        self.stationMoneySpent = 0
        """
        Initializes your Player. You can set up persistent state, do analysis
        on the input graph, engage in whatever pre-computation you need. This
        function must take less than Settings.INIT_TIMEOUT seconds.
        --- Parameters ---
        state : State
            The initial state of the game. See state.py for more information.
        """

        return

    # Checks if we can use a given path
    def path_is_valid(self, state, path):
        graph = state.get_graph()
        for i in range(0, len(path) - 1):
            if graph.edge[path[i]][path[i + 1]]['in_use']:
                return False
        return True

    def step(self, state):
        """
        Determine actions based on the current state of the city. Called every
        time step. This function must take less than Settings.STEP_TIMEOUT
        seconds.
        --- Parameters ---
        state : State
            The state of the game. See state.py for more information.
        --- Returns ---
        commands : dict list
            Each command should be generated via self.send_command or
            self.build_command. The commands are evaluated in order.
        """

        # We have implemented a naive bot for you that builds a single station
        # and tries to find the shortest path from it to first pending order.
        # We recommend making it a bit smarter ;-)

        graph = state.get_graph()
        curTime = state.get_time()
        commands = []
        self.totalProfit = state.get_money() + self.stationMoneySpent
        pending_orders = state.get_pending_orders()
        for order in pending_orders:
            x = order.get_node()
            if self.shortPath[x] is None:
                self.shortPath[x] = nx.single_source_dijkstra_path_length(graph, x)
        if not self.has_built_station:
            for x in pending_orders:
                if x.get_time_created() == curTime:
                    self.unreached.append(x.get_node())
        else:
            for x in pending_orders:
                if state.money_from(x) - DECAY_FACTOR < 0: #checks which places we never reached
                    self.unreached.append(x.get_node())

        if not self.has_built_station and curTime > self.waitTime:
            self.buildStation(state,graph,commands)

        if curTime - self.lastBuild > self.waitTime and state.get_money() > self.buildCost:
            estProfit = self.lastStationProfit/ (curTime - self.lastBuild)
            estProfit *= (1000 - curTime)
            if estProfit > self.buildCost:
                self.buildStation(state,graph,commands)


        if len(self.stations) > 0: #do not bother if we have no stations
            minLength = [100000 for x in range(len(pending_orders))] #arbitrary high value
            closestStat = [0 for x in range(len(pending_orders))]
            closestOrder = [100000 for x in range(len(self.stations))]
            closestIndex = [-1 for x in range(len(self.stations))]
            ordersFilled = [False for x in range(len(pending_orders))]
            for i in range(len(pending_orders)): # check for all stations
                for j in range(len(self.stations)):
                    station = self.stations[j]
                    x = pending_orders[i]
                    path = nx.shortest_path(graph, station, x.get_node())
                    if(len(path) < minLength[i]):
                        minLength[i] = len(path)
                        closestStat[i] = j
                if minLength[i] < closestOrder[closestStat[i]]:
                    closestOrder[closestStat[i]] = minLength[i]
                    closestIndex[closestStat[i]] = i

            for j in range(len(self.stations)):
                if not closestIndex[j] == -1 and closestOrder[j] < self.timeToDiss:
                    x = pending_orders[closestIndex[j]]
                    path = nx.shortest_path(graph, self.stations[j], x.get_node())
                    if self.path_is_valid(state, path):
                        if j == len(self.stations) - 1:
                            self.lastStationProfit += max(0,(state.money_from(x) - len(path)*DECAY_FACTOR))
                        commands.append(self.send_command(x, path))
                        ordersFilled[closestIndex[j]] = True
            for i in range(len(pending_orders)):
                if not ordersFilled[i]:
                    x = pending_orders[i]
                    j = closestStat[i]
                    path = nx.shortest_path(graph,self.stations[j],x.get_node())
                    if len(path) < self.timeToDiss:
                        if self.path_is_valid(state,path):
                            if j == len(self.stations) - 1:
                                self.lastStationProfit += max(0,(state.money_from(x) - len(path)*DECAY_FACTOR))
                            commands.append(self.send_command(x,path))

        return commands

    def findBestStation(self,state,satisfyList):
        valList = [0 for x in range(self.numNodes)]
        for x in satisfyList:
            for a in range(self.numNodes):
                if self.shortPath[x][a] <= ORDER_VAR and self.shortPath[x][a] < self.timeToDiss:
                    valList[a] += math.exp((-1 * math.pow(self.shortPath[x][a],2))/(2*math.pow(int(ORDER_VAR),2)))/ORDER_VAR
                #if self.shortPath[x][a] < self.timeToDiss and not self.shortPath[x][a] == 0:
                #    valList[a] += 1/self.shortPath[x][a]
                #elif self.shortPath[x][a] == 0:
                #    valList[a] += 2
                #valList[a] += (SCORE_MEAN - (self.shortPath[x][a] * DECAY_FACTOR))/SCORE_MEAN

        maxInd = -1
        maxVal = 0
        for a in range(self.numNodes): #find station that could serve the most nodes that are closest
            if valList[a] > maxVal:
                maxInd = a
                maxVal = valList[a]
        return maxInd

    def buildStation(self, state, graph, commands):
        best = self.findBestStation(state,self.unreached)     
        if not best == -1:    
            stat = graph.nodes()[best]
            if not stat in self.stations:
                self.stations.append(stat) 
                commands.append(self.build_command(stat))
                self.has_built_station = True
                self.stationMoneySpent += self.buildCost
                self.buildCost *= BUILD_FACTOR
                self.unreached = []
                self.lastBuild = state.get_time()
                self.lastStationProfit = 0
