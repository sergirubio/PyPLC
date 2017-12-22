
import fandango as fn 
import re
import PyTangoArchiving


class OldPLC(object):
    ## Data conversion commands---------------------------------------------------
    
    #@Catched
    @staticmethod
    def negBinary(old):
        """ Given a binary number as an string, it returns all bits negated """
        return ''.join(('0','1')[x=='0'] for x in old)

    @staticmethod
    def Denary2Binary(x,N=16):
        """ It converts an integer to an string with its binary representation 
        """ 
        if x>=0: bStr = bin(int(x))
        else: bStr = bin(int(x)%2**16)
        bStr = bStr.replace('0b','')
        if len(bStr)<N: bStr='0'*(N-len(bStr))+bStr
        return bStr[-N:]
    
    Dec2Bin = Denary2Binary
    
    @staticmethod
    def Binary2Denary(x,N=16):
        """ Converts an string with a binary number into a signed integer """
        i = int(x,2)
        if i>=2**(N-1): i=i-2**N
        return i
        
    @staticmethod
    def Exponent(n):
        """ Used in IeeeFloat type conversions, 
        Converts an array of 8 binary numbers in a signed integer. """
        sum = 0
        for x in range(0,8):
            sum += int(n[x])*pow(2,7-x)
        if sum == 0: return '0'
        sum = sum - 127
        return sum

    @staticmethod
    def Significand(n):
        """ Used in IeeeFloat type conversions """
        sum = 0.0
        pot = 1.0
        for x in range(0,24):
            sum += int(n[x])*pot/pow(2,x)
        return sum
        
    @staticmethod
    def Dec2Bits(dec,nbits=16):
        """ Decimal to binary converter """
        result,dec = [],int(dec)
        for i in range(nbits):
            result.append(bool(dec % 2))
            dec = dec >> 1
        return result        
        
    @staticmethod
    def Ints2Float(arg):
        """ Converts an array of 2 integers into an IeeeFloat number """

        reg1,reg2 = int(arg[0]),int(arg[1])
        argout = struct.unpack('d', struct.pack('LL', reg1, reg2) )[0]
        
        #Match 0 values
        bla = int(arg[1])
        if bla  == 0 and int(arg[0]) == 0: 
            return 0.0
        elif int(arg[0]) == -22939 and bla == 11195: 
            return 0.0

        #Convert high bytes
        if bla >= 0: 
            highval = PyPLC.Denary2Binary(bla)
        else:
            bla = (-1)*bla
            #"The bin value of the absolute: ",temp
            temp = PyPLC.Denary2Binary(bla) 
            #"The bin high value of the reverse: ", highval
            highval = PyPLC.negBinary(temp) 
            
        #Convert low bytes
        bla = int(arg[0])
        if bla >= 0: 
            lowval = PyPLC.Denary2Binary(bla)
        else:
            bla = (-1)*bla;
            #print "The bin value of the absolute: ",temp
            temp = PyPLC.Denary2Binary(bla)
            #print "The bin low value of the reverse: ", lowval
            lowval = PyPLC.negBinary(temp) 

        #Build result
        highval = highval + lowval

        sign = int(highval[0])
        sign1 = 1 if not sign else -1

        expo = highval[1:9]
        mant = '1' + highval[9:]

        ex = int(PyPLC.Exponent(expo))
        si = float(PyPLC.Significand(mant))
        argout= float(sign1*pow(2,ex)*si)    
    
        return argout
    
    def WriteFloat(self,argin):        
        _addr = int(argin[0])
        v = eval(str(argin[1]))
        #self.debug("In WriteFloat(%s)"%str(argin))
        try:
            p = struct.pack("!f", v)
            i = struct.unpack("!I", p)
            s = "%08x" % int(i[0])
            hw = s[:4]
            lw = s[4:]
            high = int(hw,16)
            low = int(lw,16)
            #print high, " ", low
            temph = self.Denary2Binary(high)
            templ = self.Denary2Binary(low)
            if int(temph[0]) == 1:
                bla = self.negBinary(temph)
                high = int(bla,2)
                high = (-1)*high
            if int(templ[0]) == 1:
                bla = self.negBinary(templ)
                low = int(bla,2)
                low = (-1)*low            
            arr_argin = [_addr,2,low,high]
            #self.sendModbusCommand("PresetMultipleRegisters",arr_argin)
            argout =  'LW:  %d  ,  HW:  %d' % (low,high)
            return arr_argin
            #return argin[-1]
            
        except PyTango.DevFailed, e:
            self.last_exception,self.last_exception_time = traceback.format_exc(),time.time()
            print("In WriteFloat(%s)"%str(argin)+":"+self.last_exception)
            #PyTango.Except.throw_exception(str(e.args[0]['reason']),str(e.args[0]['desc']),inspect.currentframe().f_code.co_name+':'+str(e.args[0]['origin']))
        except Exception,e:
            self.last_exception,self.last_exception_time = traceback.format_exc(),time.time()
            print("In WriteFloat(%s)"%str(argin)+":"+self.last_exception)
            #PyTango.Except.throw_exception(str(e),"Something wrong!",inspect.currentframe().f_code.co_name)    
    

class NewPLC(OldPLC):
    def Ints2Float(arg):
        """ Converts an array of 2 integers into an IeeeFloat number """

        reg1,reg2 = int(arg[0]),int(arg[1])
        import struct,traceback
        try:
            p = struct.pack('hh', reg1, reg2)
            argout = struct.unpack('f', p )[0]
        except:
            print('Ints2Float(%s) failed!'%str(arg))
            traceback.print_exc()
            


def convert_properties(device,write=False):
    
    dp = fn.get_device(device)
    prop = fn.get_device_property(device,'DynamicAttributes')
    
    r = '([^\ ]*).*[=]IeeeFloat.*AnalogRealsREAD\[([0-9]+)[:].*\].*\)(.*)'
    
    for j,p in enumerate(prop):
        m = re.match(r,p)
        if m:
            a,i,k = m.groups()
            n = '%s = IeeeFloat(AnalogRealsREAD,%s)%s'%(a,i,k)
            print(p)
            pv = dp.EvaluateFormula(p.split('=')[-1])
            nv = dp.EvaluateFormula(n.split('=')[-1])
            print(n,pv,nv)
            prop[j] = n
            print('')
            
    print('\n'.join(prop))
            
    if write:
        fn.put_device_property(device,'DynamicAttributes',prop)
        dp.updateDynamicAttributes()

    


def inspect_device(device):
    
    dp = fn.get_device(device)
    attrs = eval(dp.evaluateformula('FORMULAS'))
    mapping = eval(dp.evaluateformula('Mapping'))
    
    mapped  = [a for a,f in attrs.items() if any (m in f for m in mapping)]
    
    polled = fn.tango.get_polled_attrs(device)
    polled = [a for a in mapped if a.lower() in polled]

    rd = PyTangoArchiving.Reader()
    arch = filter(rd.is_attribute_archived,[device+'/'+a for a in mapped])
    
    used = set(map(str.lower,polled+arch))
    
    p = sum(int(l.split(',')[-1]) for l in mapping.values())
    
    return dp.MemUsage,len(mapped),len(polled),len(arch),len(used),p

#def inspect_all():



    
    
