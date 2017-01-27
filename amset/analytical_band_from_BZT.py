# coding: utf-8
from pymatgen.core.units import Energy
from scipy.constants.codata import value as _cd
from math import pi
import numpy as np

# global constants
hbar = _cd('Planck constant in eV s')/(2*pi)
m_e = _cd('electron mass') # in kg
Ry_to_eV = 13.605698066
A_to_m = 1e-10
m_to_cm = 100
e = _cd('elementary charge')

class Analytical_bands(object):
    def __init__(self, coeff_file):
        self.coeff_file = coeff_file

    def stern(self, g,nsym,symop):
        ' Compute star function for a specific g vector '

        stg=np.zeros((nsym,3))
        stg[0]=g
        nst=0

        for i in xrange(nsym):
            trial=symop[i].dot(g)
            add=True
            for m in xrange(nst):
                if np.sum(abs(trial-stg[m])) < 1e-18:
                    add=False
                    break
            if add:
                stg[nst]=trial
                nst+=1

        return nst, stg

    def get_star_functions(self, latt_points,nsym,symop,nwave,br_dir=None):
        ' Compute star functions for all R vectors and symmetries '

        nstv = np.zeros(nwave,dtype='int')
        vec = np.zeros((nwave,nsym,3))
        if br_dir != None:
            vec2 = np.zeros((nwave,nsym,3))

        for nw in xrange(nwave):
            nstv[nw], vec[nw]  = self.stern(latt_points[nw],nsym,symop)
            if br_dir != None:
                vec2[nw] = vec[nw].dot(br_dir)
        #print vec
        if br_dir!= None:
            return nstv, vec, vec2
        else:
            return nstv, vec

    def get_energy(self, xkpt,engre, latt_points, nwave, nsym, nsymop, symop, br_dir=None,cbm=True):
        ' Compute energy for a k-point from star functions '

        sign = 1
        if cbm == False:
            sign = -1

        arg = np.zeros(nsym)
        spwre = np.zeros(nwave)
        ene = 0.0

        if br_dir != None:
            dene = np.zeros(3)
            ddene = np.zeros((3,3))
            dspwre = np.zeros((nwave,3))
            ddspwre = np.zeros((nwave,3,3))
            nstv, vec, vec2 = self.get_star_functions(latt_points,nsym,symop,nwave,br_dir)
        else:
            nstv, vec = self.get_star_functions(latt_points,nsym,symop,nwave)

        for nw in xrange(nwave):
            arg = 2*np.pi*xkpt.dot(vec[nw].T)
            tempc=np.cos(arg[:nstv[nw]])
            spwre[nw]=np.sum(tempc)
            spwre[nw]/=nstv[nw]
            if br_dir != None:
                temps=np.sin(arg[:nstv[nw]])
                dspwre[nw]=np.sum(vec2[nw,:nstv[nw]].T*temps,axis=1)
                for i in xrange(nstv[nw]):
                    ddspwre[nw] += np.outer(vec2[nw,i],vec2[nw,i])*(-tempc[i])
                dspwre[nw] /= nstv[nw]
                ddspwre[nw] /= nstv[nw]

        ene=spwre.dot(engre)
        if br_dir != None:
            #TODO: in dedk, are k's fractional k's or the actual k's in the lattice? it should be changed if it's the former
            dene = np.sum(dspwre.T*engre,axis=1)
            ddene = np.sum(ddspwre*engre.reshape(nwave,1,1)*2.0,axis=0)
            return sign*ene, dene, ddene
        else:
            return sign*ene

    def get_engre(self,iband=None):
        filename = self.coeff_file
        with open(filename) as f:
            egap, nwave, nsym, nsymop=f.readline().split()
            egap, nwave, nsym, nsymop=float(egap), int(nwave), int(nsym), int(nsymop)
            br_dir = np.fromstring(f.readline(),sep=' ',count=3*3).reshape((3,3)).astype('float')
            symop=np.fromstring(f.readline(),sep=' ',count=3*3*192).reshape((192,3,3)).astype('int')
            symop=np.transpose(symop,axes=(0,2,1))
            latt_points=np.zeros((nwave,3))
            engre=np.zeros(nwave)
            for i,l in enumerate(f):
                if i<nwave:
                    latt_points[i]=np.fromstring(l,sep=' ')
                elif i == nwave:
                    bmin,bmax=np.fromstring(l,sep=' ',dtype=int)
                    if iband == None:
                        print "Bands range: {}-{}".format(bmin,bmax)
                        break
                    elif iband > bmax or iband < bmin:
                        print "ERROR! iband not in range : {}-{}".format(bmin,bmax)
                        return
                    iband2 = iband-bmin+1
                elif i == nwave+iband2:
                    engre=np.fromstring(l,sep=' ')
                    break

        return engre, latt_points, nwave, nsym, nsymop, symop, br_dir

    def get_extreme(self, kpt,iband,only_energy=False,cbm=True):
        engre,latt_points,nwave, nsym, nsymop, symop, br_dir = self.get_engre(iband)
        if only_energy == False:
            energy, denergy, ddenergy = self.get_energy(kpt,engre,latt_points, nwave, nsym, nsymop, symop, br_dir,cbm)
            return Energy(energy,"Ry").to("eV"), denergy, ddenergy
        else:
            energy = self.get_energy(kpt,engre,latt_points, nwave, nsym, nsymop, symop,cbm=cbm)
            return energy # This is in eV automatically

if __name__ == "__main__":
    # user inputs
    cbm_bidx = 11
    kpts = np.array([[0.5, 0.5, 0.5]])
    coeff_file = 'fort.123'

    analytical_bands = Analytical_bands(coeff_file=coeff_file)
    # read the coefficients file
    engre, latt_points, nwave, nsym, nsymop, symop, br_dir = analytical_bands.get_engre(iband=cbm_bidx)

    # setup
    en, den, dden = [], [], []
    for kpt in kpts:
        energy, de, dde = analytical_bands.get_energy(kpt,engre,latt_points, nwave, nsym, nsymop, symop, br_dir)
        en.append(energy*Ry_to_eV)
        den.append(de)
        dden.append(dde*2*pi)

        print("outputs:")
        print("Energy: {}".format(en))
        print("1st derivate:")
        print den
        print("2nd derivative:")
        print dde
        m_tensor = hbar ** 2 /(dde*4*pi**2) / m_e / A_to_m ** 2 * e * Ry_to_eV # m_tensor: the last part is unit conversion
        print("effective mass tensor")
        print(m_tensor)

        print("group velocity:")
        v = de /hbar*A_to_m*m_to_cm * Ry_to_eV # to get v in units of cm/s
        print v




