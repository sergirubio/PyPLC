#       "$Name:  $";
#       "$Header: /cvsroot/tango-ds/InputOutput/PyPLC/PyPLC.py,v 1.15 2012/03/20 09:09:30 sergi_rubio Exp $";
#=============================================================================
#
# file :       ModbusMap.py
#
# description : Python source for the PyPLC and its commands. 
#                The class is derived from Device. It represents the
#                CORBA servant object which will be accessed from the
#                network. All commands which can be executed on the
#                PyPLC are implemented in this file.
#
# project :     TANGO Device Server
#
# $Author:  DynamicDS and ModbusCommunications: Sergi Rubio i Manrique, srubio@cells.es; 
#            Commands and DataType management: Maciej Niegowski, mniegowski@cells.es $
#

import fandango
import fandango.functional as fun
import re,time

#Regular Expressions and Utils used in this file:
re_attr =  '[a-zA-Z]+[a-zA-Z0-9-_]*'
re_token = '[a-zA-Z]+[a-zA-Z0-9_]*'
re_float = '[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?'

match_declaration = re.compile('([a-zA-Z0-9_-]+)([:=])(.*)').match
#'match_2_addresses':lambda x: re.match('([0-9]+),([+]?[0-9]+)',x.replace(' ','')),
match_2_addresses = re.compile('([0-9]+),([+]?[0-9]+)').match
find_map_access = re.compile(re_token+'\[[0-9]+(?:[:\]])').findall
#'find_all_Regs':re.compile('(^|[^a-zA-Z])Regs[(]([0-9]+),([0-9]+)[)]').findall,
find_all_Regs = re.compile('(?:^|[^a-zA-Z])Regs(?:[(])([0-9]+),([0-9]+)[)]').findall
#'find_all_Reg':re.compile('(^|[^a-zA-Z])Reg[(]([0-9]+)[)]').findall,
find_all_Reg =  re.compile( '(?:^|[^a-zA-Z])Reg[(]([0-9]+)[)]').findall
        
class ModbusMapException(Exception):
    pass

class ModbusArray(object):
    """
    A named array of values which are continuous in PLC memory:
        DigitalsREAD = ModbusArray('DigitalsREAD=0,+100')
        read_CPUStatus = lambda:DigitalsREAD[0]
        
    Arrays can be declared as:
        a pair of addresses: DigitalsREAD=0,100
        an address range: DigitalsREAD=0,+100
        forcing a periodic update (in seconds): DigitalsWRITE=0,100,/30
    
    This class will also store the Modbus commands used to update the array
    and the start/length addresses.
    
    Every array has a "flag" attribute that can be set to True. 
    It is used from PyPLC.sendModbusCommand to mark an array that can be updated
    with the result of a freshly executed Modbus command.
    """
    MAX_REGS_LENGTH = 120 #Changed by roberto suggestion; 30/April/2009
    
    def __init__(self,declaration):
        self.declaration = declaration
        self.loglevel = 0
        #self.formula contains the previous content of a MapDict
        match = match_declaration(declaration)
        if match:
          self.name,separator,self.formula = match_declaration(declaration).groups()
          self.attribute = '%s=list(long(r) for r in ReadMap("%s"))' % (self.name,self.name)
          if re.match('[\*]?/'+re_float,self.formula.split(',')[-1]):
            self.period = fandango.str2float(self.formula.split(',')[-1])
            self.formula = self.formula.rsplit(',',1)[0]
          else: self.period = 0
        else:
          print('ModbusMap> Wrong Definition!: %s'+declaration)
          self.name,separator,self.formula,self.period,self.attribute = '','','',0,'...'
        self.commands = [] if not self.formula else self.GetCommands4Map(self.formula)
        self.start = min(c[0] for c in self.commands) if self.commands else None
        self.length = sum(c[1] for c in self.commands) if self.commands else None
        self.end = self.start+self.length if self.commands else None
        self.flag = False
        self.time = 0
        self.data = []
        self.callbacks = None
        
    @classmethod
    def is_valid_map(self,formula):
        return match_2_addresses(formula) or find_all_Regs(formula) or find_all_Reg(formula)
    
    def subscribe(self,key,callback):
        """
        Callbacks could be a tuple of (reg0, reg1, reg2, callable)
        If just a callable is passed, then it is executed for any register
        """
        if self.callbacks is None:
            self.callbacks = fandango.CaselessDict()
        if key not in self.callbacks:
            self.callbacks[key] = callback
            
    #@fandango.Cached(depth=50,expire=0.2)
    def trigger_callbacks(self,regs = None):
        if not self.callbacks: 
            return
        for key,cb in self.callbacks.items():
            try:
                if fun.isSequence(cb):
                    if not regs or any(r in cb for r in regs):
                        cb = cb[-1]
                    else:
                        continue
                #print('%s: %s.trigger(%s): callback(%s)' % 
                      #(fun.time2str(),self,key,regs or ''))
                if fun.isCallable(cb):
                    cb(key)
                else:
                    cb = getattr(cb,'push_event',
                        getattr(cb,'event_received',None))
                    cb and cb(key)
                    
            except Exception as e:
                print('%s.callback(%s): %s' % (self,cb,e))        
    
    def check(self,regs = None):
        """ 
        This flag marks some of the registers to have been just updated, 
        so ReadMap() should be called to update the array
        """
        self.flag = True
        self.time = time.time()
        return self.flag
                
    def uncheck(self):
        self.flag = False
    def checked(self):
        return self.flag
    
    def set(self,data):
        self.data = data
    def get(self,i=None):
        if i is None: return self.data
        else: return self.data[i]
    
    def has_address(self,i):
        return self.start<=i<self.end
    def get_address(self,i):
        assert self.has_address(i),'KeyError:%s'%i
        assert (i-self.start)<len(self.data),'OutOfRange:%s'%i
        return self.data[i-self.start]
    def set_address(self,i,j):
        assert self.has_address(i),"KeyError:%s"%i
        i -= self.start
        assert i<len(self.data),'OutOfRange:%s'%i
        self.data[i] = j
    
    @classmethod
    def GetCommands4Map(self,*args):
        '''
        Possible arguments are:
            2 integers (in 2 variables or in a list or tuple):
                These are understood as the starting and ending address to be read.
                Due to Modbus limitations it splits this Map reading in sets of 125 registers.
            1 string containing Regs() commands:
                The string is used like a simple attribute declaration; the attribute is evaluated.
            It returns a list of tuples containing (address,lenght) pairs
        '''        
        #self.trace('GetCommands4Map: Getting PLC Commands from %s'%str(args))
        result = []
        if len(args)==1 and isinstance(args[0],str):
            formula = args[0]
            match = match_2_addresses(formula)
            if match: 
                saddr1,saddr2 = match.groups() #This accepts two syntax, either (addr1,addr2) or (addr1,+offset)
                result = self.GetCommands4Map(int(saddr1), int(saddr1)+int(saddr2)-1 if saddr2.startswith('+') else int(saddr2))
            else: #if 'Reg' in formula:
                result.extend((int(a),int(l),) for a,l in find_all_Regs(formula))
                [result.append((int(r),1,)) for r in find_all_Reg(formula)]
        else:
            if len(args)==1 and hasattr(args[0],'__iter__'): addr1,addr2 = args[0][0],args[0][1]
            elif len(args)==2: addr1,addr2 = args[0],args[1]
            else: return []
            size = 1 + addr2-addr1 #It includes the end address in the map to be read
            i,value = 0,self.MAX_REGS_LENGTH
            while i*value<size:
                send, i = i*value , i+1
                result.append((int(addr1+send),int(size-send if (size-send)<value else value),))
        return result
        
    def trace(self,msg,level=0):
        if level<=self.loglevel: print '%s ModbusArray(%s): %s'%(fun.time2str(),self.name,msg)
        
    def __repr__(self): 
        return '%s:%s,+%s'%(self.name,self.start,self.length)
        #return '%s'%(self.attribute)
        
    def __getitem__(self,i): return self.data.__getitem__(i)
    def __getslice__(self,i,j): return self.data.__getslice__(i,j)
    def __setitem__(self,i,j): return self.data.__setitem__(i,j)
    def __contains__(self,i): return self.data.__contains__(i)
    def __bool__(self): return bool(len(self))
    def __len__(self): return self.data.__len__()
    def __iter__(self): return self.data.__iter__()
    def __reversed__(self): return self.data.__reversed__()
    def extend(self,i): return self.data.extend(i)
    def append(self,i): return self.data.append(i)
    def pop(self,i=-1): return self.data.pop(i)
    
class ModbusMap(object):
    """ 
    This class will be initialized from Mappings property of a PyPLC.
    It will provide all methods to get value of mapped addresses and mapped arrays.
    
    MyMap = ModbusMap(['DigitalsREAD=0,+100'])
    DigitalsREAD = MyModbusMap['DigitalsREAD'] #It will return an ModbusArray
    """
    
    def __init__(self,property=None,loglevel=0):
        self.mappings = {}
        self.loglevel = loglevel
        self.start = None
        self.end = None
        self.default = 0
        if property is not None: 
            self.load(property)
        
    def trace(self,msg,level=0):
        if level<=self.loglevel: print '%s ModbusMap: %s'%(fun.time2str(),msg)
        
    def load(self,property):
        """ This method initializes mapping keys from a property value (string list)"""
        for line in map(str,property):
            if '#' in line: line = line.split('#')[0]
            line = line.strip()
            if not line: continue
            #self.trace("Adding Mapping Variable: '%s'" % (line) )
            newmap = ModbusArray(line)
            self.mappings[newmap.name] = newmap
            self.start = newmap.start if self.start is None else min((newmap.start,self.start))
            self.end = newmap.end if self.end is None else max((newmap.end,self.end))
        pass
    
    def load_from_device(self,device):
        """ 
        This method allows to load ModbusMap values from a running device server 
        """
        if fandango.isString(device): device = fandango.tango.get_device(device)
        self.load(fandango.tango.get_device_property(device.name(),'Mapping'))
        [self[k].set(list(getattr(device,k))) for k in self]
        
    def export(self,filename=None):
        """ Return an array with whole memory map in a single buffer """
        buf = []
        for i in range(self.end):
            try: buf.append(self[i])
            except: buf.append(0)
        if filename:
            f = open(filename,'w')
            f.write('\n'.join(map(str,buf)))
            f.close()
            return filename
        else:
            return buf
    
    def check(self,regs=None):
        """
        This method is call from sendModbusCommand().
        Once a register is updated, all maps containing it are checked to be updated in client side.
        """
        reg = regs[0] if fun.isIterable(regs) else regs
        result = False
        for k,v in self.items():
            if v.flag: continue
            for c in v.commands:
                if c[0]<=reg<(c[0]+c[1]):
                    self.trace('In check(%s): %s Read Flag Active'%(regs,k))
                    result = v.check()
                    break #Check next map
        return result

    def __getitem__(self,key):
        if fun.isNumber(key):
            key = int(key)
            for v in self.mappings.values(): #Return a mapped addresses
                if v.has_address(key):
                    return v.get_address(key)
            if self.default is not Exception:
              return self.default
            raise Exception("AdressNotMapped: '%s'"%key)
        elif key in self.mappings: return self.mappings[key] #Return a Map
        else: raise Exception("KeyError: '%s'"%key)
    def __setitem__(self,key,value):
        if fun.isNumber(key):
            raise Exception('NotAllowed!')
        else:
            self.mappings[key].set(value)
        
    def __contains__(self,key):
        if key in self.mappings:
            return True
        elif fun.isNumber(key):
            #Return a mapped addresses
            return any(m.has_address(key) for m in self.mappings.values())
        else:
            return False
    
    def __bool__(self): return bool(len(self))
    def __len__(self): return self.end-self.start if None not in (self.end,self.start) else 0
    def __getslice__(self,i,j): return [self[x] for x in range(i,j)]
    def __iter__(self): return self.mappings.__iter__()
    def items(self): return self.mappings.items()
    def keys(self): return self.mappings.keys()
    def values(self): return self.mappings.values()
    def clear(self): self.mappings.clear()
    def asDict(self): return dict((k,v.formula) for k,v in self.items())
    def __str__(self): return str(self.asDict())
    def __repr__(self): return 'ModbusMap(%s)[%s:%s]'%(len(self),self.start,self.end)
