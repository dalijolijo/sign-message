#!/usr/bin/env python

# jackjack's signing/verifying tool
# verifies base64 signatures from Bitcoin
# signs message in three formats:
#   - Bitcoin base64 (compatible with Bitcoin)
#   - ASCII armored, Clearsign
#   - ASCII armored, Base64
#
# Licence: Public domain or CC0

import time
import hashlib
import random
import base64

FTVerbose=False

version='0.0.2'

def randomk():  #better make it stronger
	rk=0
	for i in range(8):
		rk = rk | long(random.random()*0xffffffff)<<(32*i)
	return rk

# Common constants/functions for Bitcoin

def hash_160_to_bc_address(h160, addrtype=0):
	vh160 = chr(addrtype) + h160
	h = Hash(vh160)
	addr = vh160 + h[0:4]
	return b58encode(addr)

def bc_address_to_hash_160(addr):
	bytes = b58decode(addr, 25)
	return bytes[1:21]

def Hash(data):
	return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def sha256(data):
	return hashlib.sha256(data).digest()

def sha1(data):
	return hashlib.sha1(data).digest()

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
	long_value = 0L
	for (i, c) in enumerate(v[::-1]):
		long_value += (256**i) * ord(c)

	result = ''
	while long_value >= __b58base:
		div, mod = divmod(long_value, __b58base)
		result = __b58chars[mod] + result
		long_value = div
	result = __b58chars[long_value] + result

	nPad = 0
	for c in v:
		if c == '\0': nPad += 1
		else: break

	return (__b58chars[0]*nPad) + result

def b58decode(v, length):
	long_value = 0L
	for (i, c) in enumerate(v[::-1]):
		long_value += __b58chars.find(c) * (__b58base**i)

	result = ''
	while long_value >= 256:
		div, mod = divmod(long_value, 256)
		result = chr(mod) + result
		long_value = div
	result = chr(long_value) + result

	nPad = 0
	for c in v:
		if c == __b58chars[0]: nPad += 1
		else: break

	result = chr(0)*nPad + result
	if length is not None and len(result) != length:
		return None

	return result


def regenerate_key(sec):
	b = ASecretToSecret(sec)
	if not b:
		return False
	b = b[0:32]
	secret = int('0x' + b.encode('hex'), 16)
	return EC_KEY(secret)

def GetPubKey(pkey, compressed=False):
	return i2o_ECPublicKey(pkey, compressed)

def GetPrivKey(pkey, compressed=False):
	return i2d_ECPrivateKey(pkey, compressed)

def GetSecret(pkey):
	return ('%064x' % pkey.secret).decode('hex')


def i2d_ECPrivateKey(pkey, compressed=False):#, crypted=True):
	part3='a081a53081a2020101302c06072a8648ce3d0101022100'  # for uncompressed keys
	if compressed:
		if True:#not crypted:  ## Bitcoin accepts both part3's for crypted wallets...
			part3='a08185308182020101302c06072a8648ce3d0101022100'  # for compressed keys
		key = '3081d30201010420' + \
			'%064x' % pkey.secret + \
			part3 + \
			'%064x' % _p + \
			'3006040100040107042102' + \
			'%064x' % _Gx + \
			'022100' + \
			'%064x' % _r + \
			'020101a124032200'
	else:
		key = '308201130201010420' + \
			'%064x' % pkey.secret + \
			part3 + \
			'%064x' % _p + \
			'3006040100040107044104' + \
			'%064x' % _Gx + \
			'%064x' % _Gy + \
			'022100' + \
			'%064x' % _r + \
			'020101a144034200'

	return key.decode('hex') + i2o_ECPublicKey(pkey, compressed)

def i2o_ECPublicKey(pkey, compressed=False):
	if compressed:
		if pkey.pubkey.point.y() & 1:
			key = '03' + '%064x' % pkey.pubkey.point.x()
		else:
			key = '02' + '%064x' % pkey.pubkey.point.x()
	else:
		key = '04' + \
			'%064x' % pkey.pubkey.point.x() + \
			'%064x' % pkey.pubkey.point.y()

	return key.decode('hex')

def hash_160(public_key):
 	md = hashlib.new('ripemd160')
	md.update(hashlib.sha256(public_key).digest())
	return md.digest()

def public_key_to_bc_address(public_key, v=0):
	h160 = hash_160(public_key)
	return hash_160_to_bc_address(h160, v)

def inverse_mod( a, m ):
	if a < 0 or m <= a: a = a % m
	c, d = a, m
	uc, vc, ud, vd = 1, 0, 0, 1
	while c != 0:
		q, c, d = divmod( d, c ) + ( c, )
		uc, vc, ud, vd = ud - q*uc, vd - q*vc, uc, vc
	assert d == 1
	if ud > 0: return ud
	else: return ud + m

class CurveFp( object ):
	def __init__( self, p, a, b ):
		self.__p = p
		self.__a = a
		self.__b = b

	def p( self ):
		return self.__p

	def a( self ):
		return self.__a

	def b( self ):
		return self.__b

	def contains_point( self, x, y ):
		return ( y * y - ( x * x * x + self.__a * x + self.__b ) ) % self.__p == 0

class Point( object ):
	def __init__( self, curve, x, y, order = None ):
		self.__curve = curve
		self.__x = x
		self.__y = y
		self.__order = order
		if self.__curve: assert self.__curve.contains_point( x, y )
		if order: assert self * order == INFINITY

	def __add__( self, other ):
		if other == INFINITY: return self
		if self == INFINITY: return other
		assert self.__curve == other.__curve
		if self.__x == other.__x:
			if ( self.__y + other.__y ) % self.__curve.p() == 0:
				return INFINITY
			else:
				return self.double()

		p = self.__curve.p()
		l = ( ( other.__y - self.__y ) * \
					inverse_mod( other.__x - self.__x, p ) ) % p
		x3 = ( l * l - self.__x - other.__x ) % p
		y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
		return Point( self.__curve, x3, y3 )

	def __mul__( self, other ):
		def leftmost_bit( x ):
			assert x > 0
			result = 1L
			while result <= x: result = 2 * result
			return result / 2

		e = other
		if self.__order: e = e % self.__order
		if e == 0: return INFINITY
		if self == INFINITY: return INFINITY
		assert e > 0
		e3 = 3 * e
		negative_self = Point( self.__curve, self.__x, -self.__y, self.__order )
		i = leftmost_bit( e3 ) / 2
		result = self
		while i > 1:
			result = result.double()
			if ( e3 & i ) != 0 and ( e & i ) == 0: result = result + self
			if ( e3 & i ) == 0 and ( e & i ) != 0: result = result + negative_self
			i = i / 2
		return result

	def __rmul__( self, other ):
		return self * other

	def __str__( self ):
		if self == INFINITY: return "infinity"
		return "(%d,%d)" % ( self.__x, self.__y )

	def double( self ):
		if self == INFINITY:
			return INFINITY

		p = self.__curve.p()
		a = self.__curve.a()
		l = ( ( 3 * self.__x * self.__x + a ) * \
					inverse_mod( 2 * self.__y, p ) ) % p
		x3 = ( l * l - 2 * self.__x ) % p
		y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
		return Point( self.__curve, x3, y3 )

	def x( self ):
		return self.__x

	def y( self ):
		return self.__y

	def curve( self ):
		return self.__curve

	def order( self ):
		return self.__order

INFINITY = Point( None, None, None )

def str_to_long(b):
	res = 0
	pos = 1
	for a in reversed(b):
		res += ord(a) * pos
		pos *= 256
	return res

class Public_key( object ):
	def __init__( self, generator, point, c ):
		self.curve = generator.curve()
		self.generator = generator
		self.point = point
		self.compressed = c
		n = generator.order()
		if not n:
			raise RuntimeError, "Generator point must have order."
		if not n * point == INFINITY:
			raise RuntimeError, "Generator point order is bad."
		if point.x() < 0 or n <= point.x() or point.y() < 0 or n <= point.y():
			raise RuntimeError, "Generator point has x or y out of range."

	def verify( self, hash, signature ):
		if isinstance(hash, str):
			hash=str_to_long(hash)
		G = self.generator
		n = G.order()
		r = signature.r
		s = signature.s
		if r < 1 or r > n-1: return False
		if s < 1 or s > n-1: return False
		c = inverse_mod( s, n )
		u1 = ( hash * c ) % n
		u2 = ( r * c ) % n
		xy = u1 * G + u2 * self.point
		v = xy.x() % n
		return v == r

	def ser(self):
		if self.compressed:
			if self.point.y() & 1:
				key = '03' + '%064x' % self.point.x()
			else:
				key = '02' + '%064x' % self.point.x()
		else:
			key = '04' + \
				'%064x' % self.point.x() + \
				'%064x' % self.point.y()

		return key.decode('hex')


class Signature( object ):
	def __init__( self, r, s ):
		self.r = r
		self.s = s

	def ser(self):
		return ("%064x%064x"%(self.r,self.s)).decode('hex')

class Private_key( object ):
	def __init__( self, public_key, secret_multiplier ):
		self.public_key = public_key
		self.secret_multiplier = secret_multiplier

#	def der( self ):
#		hex_der_key = '06052b8104000a30740201010420' + \
#			'%064x' % self.secret_multiplier + \
#			'a00706052b8104000aa14403420004' + \
#			'%064x' % self.public_key.point.x() + \
#			'%064x' % self.public_key.point.y()
#		return hex_der_key.decode('hex')

	def sign( self, hash, random_k ):
		if isinstance(hash, str):
			hash=str_to_long(hash)
		G = self.public_key.generator
		n = G.order()
		k = random_k % n
		p1 = k * G
		r = p1.x()
		if r == 0: raise RuntimeError, "amazingly unlucky random number r"
		s = ( inverse_mod( k, n ) * \
					( hash + ( self.secret_multiplier * r ) % n ) ) % n
		if s == 0: raise RuntimeError, "amazingly unlucky random number s"
		return Signature( r, s )

class EC_KEY(object):
	def __init__( self, secret, c=False):
		curve = CurveFp( _p, _a, _b )
		generator = Point( curve, _Gx, _Gy, _r )
		self.pubkey = Public_key( generator, generator * secret, c )
		self.privkey = Private_key( self.pubkey, secret )
		self.secret = secret

def format_msg_to_sign(msg):
    return "\x18Bitcoin Signed Message:\n"+chr(len(msg))+msg  #todo: check 18

def sqrt_mod(a, p):
    return pow(a, (p+1)/4, p)

_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L

curve_secp256k1 = CurveFp (_p, _a, _b)
generator_secp256k1 = g = Point (curve_secp256k1, _Gx, _Gy, _r)
randrange = random.SystemRandom().randrange

# Signing/verifying

def verify_message_Bitcoin(address, signature, message, pureECDSASigning=False):
    networkversion=str_to_long(b58decode(address, None)) >> (8*24)
    msg=message
    if not pureECDSASigning:
        msg=Hash(format_msg_to_sign(message))

    compressed=False
    curve = curve_secp256k1
    G = generator_secp256k1
    _a,_b,_p=curve.a(),curve.b(),curve.p()

    order = G.order()
    sig = base64.b64decode(signature)
    if len(sig) != 65:
        raise Exception("vmB","Bad signature")

    hb = ord(sig[0])
    r,s = map(str_to_long,[sig[1:33],sig[33:65]])

    if hb < 27 or hb >= 35:
        raise Exception("vmB","Bad first byte")
    if hb >= 31:
        compressed = True
        hb -= 4

    recid = hb - 27
    x = (r + (recid/2) * order) % _p
    y2 = ( pow(x,3,_p) + _a*x + _b ) % _p
    yomy = sqrt_mod(y2, _p)
    if (yomy - recid) % 2 == 0:
        y=yomy
    else:
        y=_p - yomy

    R = Point(curve, x, y, order)
    e = str_to_long(msg)
    minus_e = -e % order
    inv_r = inverse_mod(r,order)
    Q = inv_r * ( R*s + G*minus_e )

    public_key = Public_key(G, Q, compressed)
    addr = public_key_to_bc_address(public_key.ser(), networkversion)
    if address != addr:
        raise Exception("vmB","Bad address. Signing: %s, received: %s"%(addr,address))


def sign_message(secret, message, pureECDSASigning=False):
	if len(secret) == 32:
		pkey = EC_KEY(str_to_long(secret))
		compressed = False
	elif len(secret) == 33:
		pkey = EC_KEY(str_to_long(secret[:-1]))
		secret=secret[:-1]
		compressed = True
	else:
		raise Exception("sm","Bad private key size")

	msg=message
	if not pureECDSASigning:
		msg=Hash(format_msg_to_sign(message))

	eckey           = EC_KEY(str_to_long(secret), compressed)
	private_key     = eckey.privkey
	public_key      = eckey.pubkey
	addr            = public_key_to_bc_address(GetPubKey(eckey,eckey.pubkey.compressed))

	sig = private_key.sign(msg, randomk())
	if not public_key.verify(msg, sig):
		raise Exception("sm","Problem signing message")
	return [sig,addr,compressed,public_key]


def sign_message_Bitcoin(secret, msg, pureECDSASigning=False):
	sig,addr,compressed,public_key=sign_message(secret, msg, pureECDSASigning)

	for i in range(4):
		hb=27+i
		if compressed:
			hb+=4
		sign=base64.b64encode(chr(hb)+sig.ser())
		try:
			verify_message_Bitcoin(addr, sign, msg, pureECDSASigning)
			return {'address':addr, 'b64-signature':sign, 'signature':chr(hb)+sig.ser(), 'message':msg}
		except Exception as e:
#			print e.args
			pass

	raise Exception("smB","Unable to construct recoverable key")

def FormatText(t, sigctx, verbose=False):   #sigctx: False=what is displayed, True=what is signed
	r=''
	te=t.split('\n')
	for l in te:
		while len(l) and l[len(l)-1] in [' ', '\t', chr(9)]:
			l=l[:-1]
		if not len(l) or l[len(l)-1]!='\r':
			l+='\r'
		if not sigctx:
			if len(l) and l[0]=='-':
				l='- '+l[1:]
		r+=l+'\n'
	r=r[:-2]

	global FTVerbose
	if FTVerbose:
		print '  -- Sent:      '+t.encode('hex')
		if sigctx:
			print '  -- Signed:    '+r.encode('hex')
		else:
			print '  -- Displayed: '+r.encode('hex')

	return r


def crc24(m):
	INIT = 0xB704CE
	POLY = 0x1864CFB
	crc = INIT
	r = ''
	for o in m:
		o=ord(o)
		crc ^= (o << 16)
		for i in xrange(8):
			crc <<= 1
			if crc & 0x1000000:
				crc ^= POLY
	for i in range(3):
		r += chr( ( crc & (0xff<<(8*i))) >> (8*i) )
	return r

def chunks(t, n):
	return [t[i:i+n] for i in range(0, len(t), n)]

def ASCIIArmory(block, name):
	r='-----BEGIN '+name+'-----\r\n'
	r+='\r\n'.join(chunks(base64.b64encode(block), 64))+'\r\n='
	r+=base64.b64encode(crc24(block))+'\r\n'
	r+='-----END '+name+'-----'
	return r


#==============================================

def verifySignature(addr, b64sig, msg):
	return verify_message_Bitcoin(addr, b64sig, FormatText(msg, True))

def ASv0(privkey, msg):
	return sign_message_Bitcoin(privkey, FormatText(msg, True))

def ASv1CS(privkey, msg):
	sig=ASv0(privkey, msg)
	r='-----BEGIN SIGNED BITCOIN MESSAGE-----\r\n\r\n'
	r+=FormatText(msg, False)+'\r\n'
	r+=ASCIIArmory(sig['signature'], 'BITCOIN SIGNATURE')
	return r

def ASv1B64(privkey, msg):
	sig=ASv0(privkey, msg)
	return ASCIIArmory(sig['signature']+sig['message'], 'BITCOIN SIGNED MESSAGE')



#==============================================

#
#  Some tests with ugly output
#  You can delete the print commands in FormatText() after testing
#

if __name__=='__main__':
	pvk1='\x01'*32
	text0='Hello world!'
	text1='Hello world!\n'
	text2='Hello world!\n\t'
	text3='Hello world!\n-jackjack'
	text4='Hello world!\n-jackjack '
	text5='Hello world!'

	FTVerbose=True
	sv0=ASv0(pvk1, text1)
	print sv0
	verifySignature(sv0['address'], sv0['b64-signature'], sv0['message'])
	print
	print ASv1B64(pvk1, text1)
	print
	print ASv1CS(pvk1, text1)
	print
	print ASv1CS(pvk1, text2)
	print
	print ASv1CS(pvk1, text3)
	print
	print ASv1CS(pvk1, text4)
	print
	print ASv1CS(pvk1, text5)
