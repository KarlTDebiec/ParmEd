"""
This module contains an amber prmtop class that will read in all
parameters and allow users to manipulate that data and write a new
prmtop object.

Copyright (C) 2010 - 2014  Jason Swails

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
   
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""
from __future__ import division

from chemistry.periodic_table import AtomicNum, element_by_mass, Element
from chemistry import (Bond, Angle, Dihedral, AtomList, Atom, BondType,
                       AngleType, DihedralType)
from chemistry.structure import Structure
from chemistry.amber.constants import (NATOM, NTYPES, NBONH, MBONA, NTHETH,
            MTHETA, NPHIH, MPHIA, NHPARM, NPARM, NEXT, NRES, NBONA, NTHETA,
            NPHIA, NUMBND, NUMANG, NPTRA, NATYP, NPHB, IFPERT, NBPER, NGPER,
            NDPER, MBPER, MGPER, MDPER, IFBOX, NMXRS, IFCAP, NUMEXTRA, NCOPY,
            NNB)
from chemistry.amber.amberformat import AmberFormat
from chemistry.exceptions import (AmberParmError, ReadError,
                                  MoleculeError, MoleculeWarning)
try:
    from itertools import izip as zip
except ImportError:
    # This only happens in Python 3, where zip is equivalent to izip
    pass
from warnings import warn

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class AmberParm(AmberFormat, Structure):
    """
    Amber Topology (parm7 format) class. Gives low, and some high, level access
    to topology data. You can interact with the raw data in the topology file
    directly or interact with some of the high-level classes comprising the
    system topology and parameters.

    Parameters
    ----------
    prm_name : str=None
        If provided, this file is parsed and the data structures will be loaded
        from the data in this file
    rst7_name : str=None
        If provided, the coordinates and unit cell dimensions from the provided
        Amber inpcrd/restart file will be loaded into the molecule

    Attributes
    ----------
    parm_data : dict {str : list}
        A dictionary that maps FLAG names to all of the data contained in that
        section of the Amber file.
    formats : dict {str : FortranFormat}
        A dictionary that maps FLAG names to the FortranFormat instance in which
        the data is stored in that section
    parm_comments : dict {str : list}
        A dictionary that maps FLAG names to the list of COMMENT lines that were
        stored in the original file
    flag_list : list
        An ordered list of all FLAG names. This must be kept synchronized with
        `parm_data`, `formats`, and `parm_comments` such that every item in
        `flag_list` is a key to those 3 dicts and no other keys exist
    charge_flag : str='CHARGE'
        The name of the name of the FLAG that describes partial atomic charge
        data. If this flag is found, then its data are multiplied by the
        CHARGE_SCALE value attached to the current class
    version : str
        The VERSION string from the Amber file
    prm_name : str
        The file name of the originally parsed file (set to the fname parameter)
    atoms : AtomList(Atom)
        List of all atoms in the system
    residues : ResidueList(Residue)
        List of all residues in the system
    bonds : TrackedList(Bond)
        List of bonds between two atoms in the system
    angles : TrackedList(Angle)
        List of angles between three atoms in the system
    dihedrals : TrackedList(Angle)
        List of all proper and improper torsions between 4 atoms in the system
    box : list of 6 floats
        Periodic boundary unit cell dimensions and angles
    bond_types : TrackedList(BondType)
        The bond types containing the parameters for each bond stretching term
    angle_types : TrackedList(AngleType)
        The angle types containing the parameters for each angle bending term
    dihedral_types : TrackedList(DihedralType)
        The dihedral types containing the parameters for each torsional term
    bonds_inc_h : iterator(Bond)
        Read-only generator that loops through all bonds that contain Hydrogen
    bonds_without_h : iterator(Bond)
        Read-only generator that loops through all bonds that do not contain
        Hydrogen
    angles_inc_h : iterator(Angle)
        Read-only generator that loops through all angles that contain Hydrogen
    angles_without_h : iterator(Angle)
        Read-only generator that loops through all angles that do not contain
        Hydrogen
    dihedrals_inc_h : iterator(Dihedral)
        Read-only generator that loops through all dihedrals that contain
        Hydrogen
    dihedrals_without_h : iterator(Dihedral)
        Read-only generator that loops through all dihedrals that do not contain
        Hydrogen
    """
    #===================================================

    solvent_residues = ['WAT', 'HOH']

    def __init__(self, prm_name=None, rst7_name=None):
        """
        Instantiates an AmberParm object from data in prm_name and establishes
        validity based on presence of POINTERS and CHARGE sections. In general,
        you should use LoadParm from the readparm module instead. LoadParm will
        correctly dispatch the object to the 'correct' flavor of AmberParm
        """
        AmberFormat.__init__(self, prm_name)
        Structure.__init__(self)
        self.hasvels = self.hasbox = False
        if prm_name is not None:
            self.initialize_topology(rst7_name)

    #===================================================

    def initialize_topology(self, rst7_name=None):
        """
        Initializes topology data structures, like the list of atoms, bonds,
        etc., after the topology file has been read.
        """
        # We need to handle RESIDUE_ICODE properly since it may have picked up
        # some extra values
        if 'RESIDUE_ICODE' in self.flag_list:
            self._truncate_array('RESIDUE_ICODE',
                                 self.parm_data['POINTERS'][NRES])

        # instance variables other than those in AmberFormat
        self.pointers = {}   # list of all the pointers in the prmtop
        self.LJ_types = {}   # dict pairing atom name with its LJ atom type #
        self.LJ_radius = []  # ordered array of L-J radii in Ang -- indices
                             # are elements in LJ_types-1
        self.LJ_depth = []   # similarly ordered array of L-J depths

        # If we were given a prmtop, read it in
        self.load_pointers()
        self.fill_LJ()

        # Load the Structure arrays
        self.load_structure()

        # If we have coordinates or velocities, load them into the atom list
        if hasattr(self, 'coords'):
            for i, atom in enumerate(self.atoms):
                i3 = i * 3
                atom.xx, atom.xy, atom.xz = self.coords[i3:i3+3]
        if hasattr(self, 'vels'):
            for i, atom in enumerate(self.atoms):
                i3 = i * 3
                atom.vx, atom.vy, atom.vz = self.coords[i3:i3+3]

        if rst7_name is not None:
            self.LoadRst7(rst7_name)

    #===================================================

    @classmethod
    def load_from_rawdata(cls, rawdata):
        """
        Take the raw data from a AmberFormat object and initialize an AmberParm
        from that data.

        Parameters:
            - rawdata (AmberFormat): Already has a parsed file

        Returns:
            Populated AmberParm instance
        """
        inst = cls()
        inst.prm_name = rawdata.prm_name
        inst.version = rawdata.version
        inst.formats = rawdata.formats
        inst.parm_data = rawdata.parm_data
        inst.parm_comments = rawdata.parm_comments
        inst.flag_list = rawdata.flag_list
        inst.initialize_topology()
        # Convert charges if necessary due to differences in electrostatic
        # scaling factors
        chgscale = rawdata.CHARGE_SCALE / cls.CHARGE_SCALE
        for i in xrange(len(inst.parm_data['CHARGE'])):
            inst.parm_data['CHARGE'][i] *= chgscale
        # See if the rawdata has any kind of structural attributes, like rst7
        # (coordinates) and an atom list with positions and/or velocities
        if hasattr(rawdata, 'rst7'):
            inst.rst7 = rawdata.rst7
        if hasattr(rawdata, 'coords'):
            inst.load_coordinates(rawdata.coords)
        if hasattr(rawdata, 'vels'):
            inst.load_velocities(rawdata.vels)
        if hasattr(rawdata, 'box'):
            inst.box = rawdata.box
        if hasattr(rawdata, 'hasbox'):
            inst.hasbox = rawdata.hasbox
        if hasattr(rawdata, 'hasvels'):
            inst.hasvels = rawdata.hasvels
        return inst
   
    #===================================================

    def __copy__(self):
        """ Needs to copy a few additional data structures """
        other = super(AmberParm, self).__copy__()
        other.pointers = {}
        other.LJ_types = {}
        other.LJ_radius = self.LJ_radius[:]
        other.LJ_depth = self.LJ_depth[:]
        other.hasvels = self.hasvels
        other.hasbox = self.hasbox

        # Now fill the LJ and other data structures
        for p in self.pointers: other.pointers[p] = self.pointers[p]
        for typ in self.LJ_types: other.LJ_types[typ] = self.LJ_types[typ]
        try:
            other.load_structure()
        except (KeyError, IndexError, AttributeError):
            raise AmberParmError('Could not set up topology for parm copy')
        # See if we have a restart file
        if hasattr(self, 'rst7'):
            other.rst7 = Rst7.copy_from(self.rst7)
        # Now we should have a full copy
        return other

    #===================================================
   
    def load_pointers(self):
        """
        Loads the data in POINTERS section into a pointers dictionary with each
        key being the pointer name according to http://ambermd.org/formats.html
        """
        self.pointers["NATOM"] = self.parm_data["POINTERS"][NATOM]
        self.pointers["NTYPES"] = self.parm_data["POINTERS"][NTYPES]
        self.pointers["NBONH"] = self.parm_data["POINTERS"][NBONH]
        self.pointers["MBONA"] = self.parm_data["POINTERS"][MBONA]
        self.pointers["NTHETH"] = self.parm_data["POINTERS"][NTHETH]
        self.pointers["MTHETA"] = self.parm_data["POINTERS"][MTHETA]
        self.pointers["NPHIH"] = self.parm_data["POINTERS"][NPHIH]
        self.pointers["MPHIA"] = self.parm_data["POINTERS"][MPHIA]
        self.pointers["NHPARM"] = self.parm_data["POINTERS"][NHPARM]
        self.pointers["NPARM"] = self.parm_data["POINTERS"][NPARM]
        self.pointers["NEXT"] = self.parm_data["POINTERS"][NEXT]
        self.pointers["NNB"] = self.parm_data["POINTERS"][NNB] # alias for above
        self.pointers["NRES"] = self.parm_data["POINTERS"][NRES]
        self.pointers["NBONA"] = self.parm_data["POINTERS"][NBONA]
        self.pointers["NTHETA"] = self.parm_data["POINTERS"][NTHETA]
        self.pointers["NPHIA"] = self.parm_data["POINTERS"][NPHIA]
        self.pointers["NUMBND"] = self.parm_data["POINTERS"][NUMBND]
        self.pointers["NUMANG"] = self.parm_data["POINTERS"][NUMANG]
        self.pointers["NPTRA"] = self.parm_data["POINTERS"][NPTRA]
        self.pointers["NATYP"] = self.parm_data["POINTERS"][NATYP]
        self.pointers["NPHB"] = self.parm_data["POINTERS"][NPHB]
        self.pointers["IFPERT"] = self.parm_data["POINTERS"][IFPERT]
        self.pointers["NBPER"] = self.parm_data["POINTERS"][NBPER]
        self.pointers["NGPER"] = self.parm_data["POINTERS"][NGPER]
        self.pointers["NDPER"] = self.parm_data["POINTERS"][NDPER]
        self.pointers["MBPER"] = self.parm_data["POINTERS"][MBPER]
        self.pointers["MGPER"] = self.parm_data["POINTERS"][MGPER]
        self.pointers["MDPER"] = self.parm_data["POINTERS"][MDPER]
        self.pointers["IFBOX"] = self.parm_data["POINTERS"][IFBOX]
        self.pointers["NMXRS"] = self.parm_data["POINTERS"][NMXRS]
        self.pointers["IFCAP"] = self.parm_data["POINTERS"][IFCAP]
        self.pointers["NUMEXTRA"] = self.parm_data["POINTERS"][NUMEXTRA]
        if self.parm_data['POINTERS'][IFBOX] > 0:
            self.pointers['IPTRES'] = self.parm_data['SOLVENT_POINTERS'][0]
            self.pointers['NSPM'] = self.parm_data['SOLVENT_POINTERS'][1]
            self.pointers['NSPSOL'] = self.parm_data['SOLVENT_POINTERS'][2]
        # The next is probably only there for LES-prmtops
        try:
            self.pointers["NCOPY"] = self.parm_data["POINTERS"][NCOPY]
        except:
            pass

    #===================================================

    def load_structure(self):
        """ 
        Loads all of the topology instance variables. This is necessary if we
        actually want to modify the topological layout of our system
        (like deleting atoms)
        """
        self._check_section_lengths()
        self._load_atoms_and_residues()
        self.load_atom_info()
        self._load_bond_info()
        self._load_angle_info()
        self._load_dihedral_info()
        super(AmberParm, self).unchange()

    #===================================================

    def load_atom_info(self):
        """
        Loads atom properties into the atoms that have been loaded. If any
        arrays are too short or too long, an IndexError will be raised
        """
        # Collect all of the atom properties present in our topology file
        zeros = _zeros(len(self.atoms))
        anam = self.parm_data['ATOM_NAME']
        chg = self.parm_data['CHARGE']
        mass = self.parm_data['MASS']
        nbtyp = self.parm_data['ATOM_TYPE_INDEX']
        atyp = self.parm_data['AMBER_ATOM_TYPE']
        join = self.parm_data['JOIN_ARRAY']
        irot = self.parm_data['IROTAT']
        tree = self.parm_data['TREE_CHAIN_CLASSIFICATION']
        try:
            radii = self.parm_data['RADII']
        except KeyError:
            radii = zeros
        try:
            screen = self.parm_data['SCREEN']
        except KeyError:
            screen = zeros
        try:
            atnum = self.parm_data['ATOMIC_NUMBER']
        except KeyError:
            atnum = [AtomicNum[element_by_mass(m)] for m in mass]
        for i, atom in enumerate(self.atoms):
            atom.name = anam[i]
            atom.charge = chg[i]
            atom.mass = mass[i]
            atom.nb_idx = nbtyp[i]
            atom.type = atyp[i]
            atom.join = join[i]
            atom.irotat = irot[i]
            atom.tree = tree[i]
            atom.radii = radii[i]
            atom.screen = screen[i]
            atom.atomic_number = atnum[i]

    #===================================================

    def __str__(self):
        " Returns the name of the topology file as its string representation "
        if self.prm_name is not None:
            return self.prm_name
        return repr(self)

    #===================================================

    def ptr(self, pointer):
        """
        Returns the value of the given pointer, and converts to upper-case so
        it's case-insensitive. A non-existent pointer meets with a KeyError

        Parameters
        ----------
        pointer : str
            The AMBER pointer for which to extract the value

        Returns
        -------
        int
            The returned integer is the value of that pointer
        """
        return self.pointers[pointer.upper()]

    #===================================================

    def writeRst7(self, name, netcdf=None):
        """
        Writes a restart file with the current coordinates and velocities and
        box info if it's present
        """
        # By default, determine file type by extension (.ncrst is NetCDF)
        netcdf = netcdf or (netcdf is None and name.endswith('.ncrst'))

        # Check that we have a rst7 loaded, then overwrite it with a new one if
        # necessary
        if not hasattr(self, 'rst7'):
#           raise AmberParmError('No coordinates loaded. Cannot write restart')
            self.rst7 = Rst7(hasbox=self.hasbox)
            if self.hasbox:
                self.rst7.box = self.box

        # Now fill in the rst7 coordinates
        self.rst7.natom = len(self.atoms)
        self.rst7.coordinates = [0.0 for i in xrange(len(self.atoms)*3)]
        if self.rst7.hasvels:
            self.rst7.velocities = [0.0 for i in xrange(len(self.atoms)*3)]

        for i, at in enumerate(self.atoms):
            self.rst7.coordinates[3*i  ] = at.xx
            self.rst7.coordinates[3*i+1] = at.xy
            self.rst7.coordinates[3*i+2] = at.xz
            if self.rst7.hasvels:
                self.rst7.velocities[3*i  ] = at.vx
                self.rst7.velocities[3*i+1] = at.vy
                self.rst7.velocities[3*i+2] = at.vz

        # Now write the restart file
        self.rst7.write(name, netcdf)

    #===================================================

    def write_parm(self, name):
        """
        Writes the current data in parm_data into a new topology file with a
        given name.
        """
        if self.is_changed():
            self.remake_parm()
#           self.load_structure()

        AmberFormat.write_parm(self, name)

    #===================================================

    def remake_parm(self):
        """
        Re-fills the topology file arrays if we have changed the underlying
        structure
        """
        # Get rid of terms containing deleted atoms and empty residues
        self.prune_empty_terms()
        self.residues.prune()

        # Transfer information from the topology lists 
        self._xfer_atom_properties()
        self._xfer_residue_properties()
        self._xfer_bond_properties()
        self._xfer_angle_properties()
        self._xfer_dihedral_properties()
        self.rediscover_molecules()
        # Mark atom list as unchanged
        super(AmberParm, self).unchange()

    #===================================================
   
    def is_changed(self):
        """ 
        Determines if any of the topological arrays have changed since the
        last upload
        """
        is_changed = super(AmberParm, self).is_changed()
        if is_changed and hasattr(self, '_topology'):
            del self._topology
        return is_changed

    #===================================================

    def delete_mask(self, mask):
        """
        Deletes all of the atoms corresponding to an entire Amber mask

        Parameters
        ----------
        mask : str or AmberMask
            The Amber mask defining the selection of atoms that will be deleted
            from this topology
        """
        from chemistry.amber.mask import AmberMask
        # Get the atom selection
        if isinstance(mask, AmberMask):
            if mask.parm is not self:
                raise AmberParmError('Mask belongs to different prmtop!')
            selection = reversed(list(mask.Selected()))
        else:
            selection = reversed(list(AmberMask(self, mask).Selected()))
        # Delete the atoms and rebuild the topology and coordinates
        for i in selection:
            del self.atoms[i]
        self.remake_parm()
        if hasattr(self, 'coords'):
            self.coords = []
            for atom in self.atoms:
                self.coords.extend([atom.xx, atom.xy, atom.xz])
            if self.hasvels:
                for atom in self.atoms:
                    self.vels.extend([atom.vx, atom.vy, atom.vz])
#       self.load_structure()
        if self.ptr('IFBOX'): self.rediscover_molecules()

    #===================================================

    def rediscover_molecules(self, solute_ions=True, fix_broken=True):
        """
        This determines the molecularity and sets the ATOMS_PER_MOLECULE and
        SOLVENT_POINTERS sections of the prmtops. Returns the new atom sequence
        in terms of the 'old' atom indexes if re-ordering was necessary to fix
        the tleap bug. Returns None otherwise.
        """
        # Bail out of we are not doing a solvated prmtop
        if not self.parm_data['POINTERS'][IFBOX]: return None

        owner = set_molecules(self)
        ions = ['Br-','Cl-','Cs+','F-','I-','K+','Li+','Mg+','Na+','Rb+','IB',
                'CIO','MG2']
        indices = []
        for res in AmberParm.solvent_residues:
            try:
                indices.append(self.parm_data['RESIDUE_LABEL'].index(res))
            except ValueError:
                pass
        # Add ions to list of solvent if necessary
        if not solute_ions:
            for ion in ions:
                if ion in self.parm_data['RESIDUE_LABEL']:
                    indices.append(self.parm_data['RESIDUE_LABEL'].index(ion))
        # If we have no water, we do not have a molecules section!
        if not indices:
            self.parm_data['POINTERS'][IFBOX] = 0
            self.pointers['IFBOX'] = 0
            del self.pointers['IPTRES']
            del self.pointers['NSPM']
            del self.pointers['NSPSOL']
            self.delete_flag('SOLVENT_POINTERS')
            self.delete_flag('ATOMS_PER_MOLECULE')
            self.delete_flag('BOX_DIMENSIONS')
            self.hasbox = False
            try: 
                self.rst7.hasbox = False
                del self.box
                del self.rst7.box
            except AttributeError:
                # So we don't have box information... doesn't matter :)
                pass
            return None
        # Now remake our SOLVENT_POINTERS and ATOMS_PER_MOLECULE section
        self.parm_data['SOLVENT_POINTERS'] = [min(indices), len(owner), 0]
        first_solvent = self.parm_data['RESIDUE_POINTER'][min(indices)]
        # Find the first solvent molecule
        for i, mol in enumerate(owner):
            if first_solvent-1 == mol[0]:
                self.parm_data['SOLVENT_POINTERS'][2] = i + 1
                break
        else: # this else belongs to 'for', not 'if'
            raise MoleculeError('Could not find first solvent atom!')

        # Now set up ATOMS_PER_MOLECULE and catch any errors
        self.parm_data['ATOMS_PER_MOLECULE'] = [len(mol) for mol in owner]

        # Check that all of our molecules are contiguous, because we have to
        # re-order atoms if they're not
        try:
            for mol in owner:
                for i in xrange(1, len(mol)):
                    if mol[i] != mol[i-1] + 1:
                        raise StopIteration()
        except StopIteration:
            if not fix_broken:
                raise MoleculeError('Molecule atoms are not contiguous!')
            # Non-contiguous molecules detected... time to fix (ugh!)
            warn('Molecule atoms are not contiguous! I am attempting to '
                 'reorder the atoms to fix this.', MoleculeWarning)
            new_atoms = AtomList()
            for mol in owner:
                for atom in mol:
                    new_atoms.append(atom)
            self.atoms = new_atoms
            return owner

        return None

    #===================================================

    def writeOFF(self, off_file='off.lib'):
        """ Writes an OFF file from all of the residues found in a prmtop """
        from chemistry.amber.residue import ToResidue
   
        off_file = open(off_file, 'w')
   
        # keep track of all the residues we have to print to the OFF file
        residues = []
   
        # First create a Molecule object from the prmtop
        mol = self.ToMolecule()
   
        # Now loop through all of the residues in the Molecule object and add
        # unique ones to the list of residues to print
        for i in xrange(len(mol.residues)):
            res = ToResidue(mol, i)
            present = False
            for compres in residues:
                if res == compres:
                    present = True
   
            if not present:
                residues.append(res)
      
        # Now that we have all of the residues that we need to add, put their
        # names in the header of the OFF file
        off_file.write('!!index array str\n')
        for res in residues:
            off_file.write(' "%s"\n' % res.name)
   
        # Now write the OFF strings to the file
        for res in residues:
            off_file.write(res.OFF())

        off_file.close()

    #===================================================

    def fill_LJ(self):
        """
        Fills the LJ_radius, LJ_depth arrays and LJ_types dictionary with data
        from LENNARD_JONES_ACOEF and LENNARD_JONES_BCOEF sections of the prmtop
        files, by undoing the canonical combining rules.
        """
        self.LJ_radius = []  # empty LJ_radii so it can be re-filled
        self.LJ_depth = []   # empty LJ_depths so it can be re-filled
        self.LJ_types = {}   # empty LJ_types so it can be re-filled
        one_sixth = 1 / 6    # we need to raise some numbers to the 1/6th power

        pd = self.parm_data
        acoef = pd['LENNARD_JONES_ACOEF']
        bcoef = pd['LENNARD_JONES_BCOEF']
        natom = self.pointers['NATOM']
        ntypes = self.pointers['NTYPES']
        for i in xrange(natom): # fill the LJ_types array
            self.LJ_types[pd["AMBER_ATOM_TYPE"][i]] = pd["ATOM_TYPE_INDEX"][i]
         
        for i in xrange(ntypes):
            lj_index = pd["NONBONDED_PARM_INDEX"][ntypes*i+i] - 1
            if pd["LENNARD_JONES_ACOEF"][lj_index] < 1.0e-10:
                self.LJ_radius.append(0)
                self.LJ_depth.append(0)
            else:
                factor = 2 * acoef[lj_index] / bcoef[lj_index]
                self.LJ_radius.append(pow(factor, one_sixth) * 0.5)
                self.LJ_depth.append(bcoef[lj_index] / 2 / factor)

    #===================================================

    def fill_14_LJ(self):
        """
        Fills the LJ_14_radius, LJ_14_depth arrays with data (LJ_types is
        identical) from LENNARD_JONES_14_ACOEF and LENNARD_JONES_14_BCOEF
        sections of the prmtop files, by undoing the canonical combining rules.
        """
        if not self.chamber:
            raise TypeError('fill_14_LJ() only valid on a chamber prmtop!')

        pd = self.parm_data
        acoef = pd['LENNARD_JONES_14_ACOEF']
        bcoef = pd['LENNARD_JONES_14_BCOEF']
        ntypes = self.pointers['NTYPES']

        self.LJ_14_radius = []  # empty LJ_radii so it can be re-filled
        self.LJ_14_depth = []   # empty LJ_depths so it can be re-filled
        one_sixth = 1.0 / 6.0 # we need to raise some numbers to the 1/6th power

        for i in xrange(ntypes):
            lj_index = pd["NONBONDED_PARM_INDEX"][ntypes*i+i] - 1
            if acoef[lj_index] < 1.0e-6:
                self.LJ_14_radius.append(0)
                self.LJ_14_depth.append(0)
            else:
                factor = 2 * acoef[lj_index] / bcoef[lj_index]
                self.LJ_14_radius.append(pow(factor, one_sixth) * 0.5)
                self.LJ_14_depth.append(bcoef[lj_index] / 2 / factor)

    #===================================================

    def recalculate_LJ(self):
        """
        Takes the values of the LJ_radius and LJ_depth arrays and recalculates
        the LENNARD_JONES_A/BCOEF topology sections from the canonical combining
        rules.
        """
        pd = self.parm_data
        ntypes = self.pointers['NYTPES']
        for i in xrange(ntypes):
            for j in xrange(i, ntypes):
                index = pd['NONBONDED_PARM_INDEX'][ntypes*i+j] - 1
                rij = self.combine_rmin(self.LJ_radius[i], self.LJ_radius[j])
                wdij = self.combine_epsilon(self.LJ_depth[i], self.LJ_depth[j])
                pd["LENNARD_JONES_ACOEF"][index] = wdij * rij**12
                pd["LENNARD_JONES_BCOEF"][index] = 2 * wdij * rij**6

    #===================================================

    def recalculate_14_LJ(self):
        """
        Takes the values of the LJ_radius and LJ_depth arrays and recalculates
        the LENNARD_JONES_A/BCOEF topology sections from the canonical combining
        rules for the 1-4 LJ interactions (CHAMBER only)
        """
        if not self.chamber:
            raise TypeError('recalculate_14_LJ() requires a CHAMBER prmtop!')

        pd = self.parm_data
        ntypes = self.pointers['NYTPES']
        for i in xrange(ntypes):
            for j in xrange(i, ntypes):
                index = pd['NONBONDED_PARM_INDEX'][ntypes*i+j] - 1
                rij = self.combine_rmin(
                        self.LJ_14_radius[i],self.LJ_14_radius[j]
                )
                wdij = self.combine_epsilon(
                        self.LJ_14_depth[i],self.LJ_14_depth[j]
                )
                pd["LENNARD_JONES_14_ACOEF"][index] = wdij * rij**12
                pd["LENNARD_JONES_14_BCOEF"][index] = 2 * wdij * rij**6

    #===================================================

    def LoadRst7(self, rst7):
        """ Loads coordinates into the AmberParm class """
        if isinstance(rst7, Rst7):
            self.rst7 = rst7
        elif isinstance(rst7, basestring):
            self.rst7 = Rst7.open(rst7)
        self.load_coordinates(self.rst7.coordinates)
        self.hasvels = self.rst7.hasvels
        self.hasbox = self.rst7.hasbox
        if self.hasbox:
            self.box = self.rst7.box
        if self.hasvels:
            self.load_velocities(self.rst7.velocities)

    #===================================================

    def load_coordinates(self, coords):
        """ Loads the coordinates into the atom list """
        self.coords = coords
        for i, atom in enumerate(self.atoms):
            i3 = 3 * i
            atom.xx = coords[i3  ]
            atom.xy = coords[i3+1]
            atom.xz = coords[i3+2]

    #===================================================

    def load_velocities(self, vels):
        """ Loads the coordinates into the atom list """
        self.hasvels = True
        self.vels = vels
        for i, atom in enumerate(self.atoms):
            i3 = 3 * i
            atom.vx = vels[i3  ]
            atom.vy = vels[i3+1]
            atom.vz = vels[i3+2]

    #===================================================

    # Iterators for parameters with and without hydrogen
    @property
    def bonds_inc_h(self):
        """ All bonds including hydrogen """
        for bond in self.bonds:
            if (bond.atom1.atomic_number == 1 or
                    bond.atom2.atomic_number == 1):
                yield bond

    @property
    def bonds_without_h(self):
        """ All bonds without hydrogen """
        for bond in self.bonds:
            if (bond.atom1.atomic_number == 1 or
                    bond.atom2.atomic_number == 1):
                continue
            yield bond

    @property
    def angles_inc_h(self):
        """ All angles including hydrogen """
        for angle in self.angles:
            if (angle.atom1.atomic_number == 1 or angle.atom2.atomic_number == 1
                    or angle.atom3.atomic_number == 1):
                yield angle

    @property
    def angles_without_h(self):
        """ All angles including hydrogen """
        for angle in self.angles:
            if (angle.atom1.atomic_number == 1 or angle.atom2.atomic_number == 1
                    or angle.atom3.atomic_number == 1):
                continue
            yield angle

    @property
    def dihedrals_inc_h(self):
        """ All dihedrals including hydrogen """
        for dihed in self.dihedrals:
            if (dihed.atom1.atomic_number == 1
                    or dihed.atom2.atomic_number == 1
                    or dihed.atom3.atomic_number == 1
                    or dihed.atom4.atomic_number == 1):
                yield dihed

    @property
    def dihedrals_without_h(self):
        """ All dihedrals including hydrogen """
        for dihed in self.dihedrals:
            if (dihed.atom1.atomic_number == 1
                    or dihed.atom2.atomic_number == 1
                    or dihed.atom3.atomic_number == 1
                    or dihed.atom4.atomic_number == 1):
                continue
            yield dihed

    #===================================================

    @property
    def chamber(self):
        return False

    @property
    def amoeba(self):
        return False

    #===========  PRIVATE INSTANCE METHODS  ============

    def _truncate_array(self, section, length):
        """ Truncates an array to get the given length """
        self.parm_data[section] = self.parm_data[section][:length]

    #===================================================

    def _check_section_lengths(self):
        """
        Checks that all of the raw sections have the appropriate length as
        specified by the POINTER section.

        If any of the lengths are incorrect, AmberParmError is raised
        """
        def check_length(key, length, required=True):
            if not required and key not in self.parm_data: return
            if len(self.parm_data[key]) != length:
                raise AmberParmError('FLAG %s has %d elements; expected %d' %
                                     (key, len(self.parm_data[key]), length))
        natom = self.ptr('NATOM')
        check_length('ATOM_NAME', natom)
        check_length('CHARGE', natom)
        check_length('MASS', natom)
        check_length('ATOM_TYPE_INDEX', natom)
        check_length('NUMBER_EXCLUDED_ATOMS', natom)
        check_length('JOIN_ARRAY', natom)
        check_length('IROTAT', natom)
        check_length('RADIUS', natom, False)
        check_length('SCREEN', natom, False)
        check_length('ATOMIC_NUMBER', natom, False)

        ntypes = self.ptr('NTYPES')
        check_length('NONBONDED_PARM_INDEX', ntypes*ntypes)
        check_length('LENNARD_JONES_ACOEF', ntypes*(ntypes+1)//2)
        check_length('LENNARD_JONES_BCOEF', ntypes*(ntypes+1)//2)
        check_length('LENNARD_JONES_CCOEF', ntypes*(ntypes+1)//2, False)

        nres = self.ptr('NRES')
        check_length('RESIDUE_LABEL', nres)
        check_length('RESIDUE_POINTER', nres)
        check_length('RESIDUE_CHAINID', nres, False)
        check_length('RESIDUE_ICODE', nres, False)
        check_length('RESIDUE_NUMBER', nres, False)

        check_length('BOND_FORCE_CONSTANT', self.ptr('NUMBND'))
        check_length('BOND_EQUIL_VALUE', self.ptr('NUMBND'))
        check_length('ANGLE_FORCE_CONSTANT', self.ptr('NUMANG'))
        check_length('ANGLE_EQUIL_VALUE', self.ptr('NUMANG'))
        check_length('DIHEDRAL_FORCE_CONSTANT', self.ptr('NPTRA'))
        check_length('DIHEDRAL_PERIODICITY', self.ptr('NPTRA'))
        check_length('DIHEDRAL_PHASE', self.ptr('NPTRA'))
        check_length('SCEE_SCALE_FACTOR', self.ptr('NPTRA'), False)
        check_length('SCNB_SCALE_FACTOR', self.ptr('NPTRA'), False)
        check_length('SOLTY', self.ptr('NATYP'))
        check_length('BONDS_INC_HYDROGEN', self.ptr('NBONH')*3)
        check_length('BONDS_WITHOUT_HYDROGEN', self.ptr('MBONA')*3)
        check_length('ANGLES_INC_HYDROGEN', self.ptr('NTHETH')*4)
        check_length('ANGLES_WITHOUT_HYDROGEN', self.ptr('NTHETA')*4)
        check_length('DIHEDRALS_INC_HYDROGEN', self.ptr('NPHIH')*5)
        check_length('DIHEDRALS_WITHOUT_HYDROGEN', self.ptr('NPHIA')*5)
        check_length('HBOND_ACOEF', self.ptr('NPHB'))
        check_length('HBOND_BCOEF', self.ptr('NPHB'))
        check_length('SOLVENT_POINTERS', 3, False)
        if 'SOLVENT_POINTERS' in self.parm_data:
            check_length('ATOMS_PER_MOLECULE',
                         self.parm_data['SOLVENT_POINTERS'][1], False)

    #===================================================

    def _load_atoms_and_residues(self):
        """
        Loads the atoms and residues (which are always done together) into the
        data structure
        """
        del self.residues[:]
        del self.atoms[:]
        # Figure out on which atoms the residues start and stop
        natom = self.parm_data['POINTERS'][NATOM]
        res_ptr = self.parm_data['RESIDUE_POINTER'] + [natom+1]
        try:
            res_icd = self.parm_data['RESIDUE_ICODE']
        except KeyError:
            res_icd = ['' for i in xrange(self.parm_data['POINTERS'][NRES])]
        try:
            res_chn = self.parm_data['RESIDUE_CHAINID']
        except KeyError:
            res_chn = ['' for i in xrange(self.parm_data['POINTERS'][NRES])]
        for i, resname in enumerate(self.parm_data['RESIDUE_LABEL']):
            resstart = res_ptr[i] - 1
            resend = res_ptr[i+1] - 1
            for j in range(resstart, resend):
                atom = Atom()
                self.residues.add_atom(atom, resname, i, res_chn[i], res_icd[i])
                self.atoms.append(atom)

    #===================================================

    def _load_bond_info(self):
        """ Loads the bond types and bond arrays """
        del self.bond_types[:]
        del self.bonds[:]
        for k, req in zip(self.parm_data['BOND_FORCE_CONSTANT'],
                          self.parm_data['BOND_EQUIL_VALUE']):
            self.bond_types.append(BondType(k, req, self.bond_types))
        blist = self.parm_data['BONDS_INC_HYDROGEN']
        for i in xrange(0, 3*self.parm_data['POINTERS'][NBONH], 3):
            self.bonds.append(
                    Bond(self.atoms[blist[i]//3], self.atoms[blist[i+1]//3],
                         self.bond_types[blist[i+2]-1])
            )
        blist = self.parm_data['BONDS_WITHOUT_HYDROGEN']
        for i in xrange(0, 3*self.parm_data['POINTERS'][MBONA], 3):
            self.bonds.append(
                    Bond(self.atoms[blist[i]//3], self.atoms[blist[i+1]//3],
                            self.bond_types[blist[i+2]-1])
            )

    #===================================================

    def _load_angle_info(self):
        """ Loads the angle types and angle arrays """
        del self.angle_types[:]
        del self.angles[:]
        for k, theteq in zip(self.parm_data['ANGLE_FORCE_CONSTANT'],
                             self.parm_data['ANGLE_EQUIL_VALUE']):
            self.angle_types.append(AngleType(k, theteq, self.angle_types))
        alist = self.parm_data['ANGLES_INC_HYDROGEN']
        for i in xrange(0, 4*self.parm_data['POINTERS'][NTHETH], 4):
            self.angles.append(
                    Angle(self.atoms[alist[i]//3],
                          self.atoms[alist[i+1]//3],
                          self.atoms[alist[i+2]//3],
                          self.angle_types[alist[i+3]-1])
            )
        alist = self.parm_data['ANGLES_WITHOUT_HYDROGEN']
        for i in xrange(0, 4*self.parm_data['POINTERS'][MTHETA], 4):
            self.angles.append(
                    Angle(self.atoms[alist[i]//3],
                          self.atoms[alist[i+1]//3],
                          self.atoms[alist[i+2]//3],
                          self.angle_types[alist[i+3]-1])
            )

    #===================================================

    def _load_dihedral_info(self):
        """ Loads the dihedral types and dihedral arrays """
        del self.dihedral_types[:]
        del self.dihedrals[:]
        try:
            scee = self.parm_data['SCEE_SCALE_FACTOR']
        except KeyError:
            scee = [1.2 for i in self.parm_data['DIHEDRAL_FORCE_CONSTANT']]
        try:
            scnb = self.parm_data['SCNB_SCALE_FACTOR']
        except KeyError:
            scnb = [1.2 for i in self.parm_data['DIHEDRAL_FORCE_CONSTANT']]
        for terms in zip(self.parm_data['DIHEDRAL_FORCE_CONSTANT'],
                         self.parm_data['DIHEDRAL_PERIODICITY'],
                         self.parm_data['DIHEDRAL_PHASE'],
                         scee, scnb):
            self.dihedral_types.append(
                    DihedralType(*terms, list=self.dihedral_types)
            )
        dlist = self.parm_data['DIHEDRALS_INC_HYDROGEN']
        for i in xrange(0, 5*self.parm_data['POINTERS'][NPHIH], 5):
            ignore_end = dlist[i+2] < 0
            improper = dlist[i+3] < 0
            self.dihedrals.append(
                    Dihedral(self.atoms[dlist[i]//3],
                             self.atoms[dlist[i+1]//3],
                             self.atoms[abs(dlist[i+2])//3],
                             self.atoms[abs(dlist[i+3])//3],
                             improper=improper, ignore_end=ignore_end,
                             type=self.dihedral_types[dlist[i+4]-1])
            )
        dlist = self.parm_data['DIHEDRALS_WITHOUT_HYDROGEN']
        for i in xrange(0, 5*self.parm_data['POINTERS'][MPHIA], 5):
            ignore_end = dlist[i+2] < 0
            improper = dlist[i+3] < 0
            self.dihedrals.append(
                    Dihedral(self.atoms[dlist[i]//3],
                             self.atoms[dlist[i+1]//3],
                             self.atoms[abs(dlist[i+2])//3],
                             self.atoms[abs(dlist[i+3])//3],
                             improper=improper, ignore_end=ignore_end,
                             type=self.dihedral_types[dlist[i+4]-1])
            )

    #===================================================

    def _xfer_atom_properties(self):
        """
        Sets the various topology file section data from the `atoms` list to the
        topology file data in `parm_data`
        """
        natom = len(self.atoms)
        data = self.parm_data
        data['POINTERS'][NATOM] = natom
        self.pointers['NATOM'] = natom
        data['ATOM_NAME'] = [atom.name for atom in self.atoms]
        data['CHARGE'] = [atom.charge for atom in self.atoms]
        data['MASS'] = [atom.mass for atom in self.atoms]
        data['ATOM_TYPE_INDEX'] = [atom.nb_idx for atom in self.atoms]
        data['JOIN_ARRAY'] = [atom.join for atom in self.atoms]
        data['TREE_CHAIN_CLASSIFICATION'] = [atom.tree for atom in self.atoms]
        data['IROTAT'] = [atom.irotat for atom in self.atoms]
        if 'RADII' in data:
            data['RADII'] = [atom.radii for atom in self.atoms]
        if 'SCREEN' in data:
            data['SCREEN'] = [atom.screen for atom in self.atoms]
        if 'ATOMIC_NUMBER' in data:
            data['ATOMIC_NUMBER'] = [atom.atomic_number for atom in self.atoms]
        # Do the non-bonded exclusions now
        data['EXCLUDED_ATOMS_LIST'] = []
        nextra = 0
        for i, atom in enumerate(self.atoms):
            excl = atom.nonbonded_exclusions(index_from=1)
            if len(excl) == 0:
                excl = [0]
            data['EXCLUDED_ATOMS_LIST'] += excl
            data['NUMBER_EXCLUDED_ATOMS'][i] = len(excl)
            if atom.atomic_number == 0:
                nextra += 1
        nnb = len(data['EXCLUDED_ATOMS_LIST'])
        data['POINTERS'][NNB] = nnb
        self.pointers['NNB'] = self.pointers['NEXT'] = nnb
        data['POINTERS'][NUMEXTRA] = nextra
        self.pointers['NUMEXTRA'] = nextra

    #===================================================

    def _xfer_residue_properties(self):
        """
        Sets the various topology file section data from the `residues` list to
        the topology file data in `parm_data`
        """
        data = self.parm_data
        nres = len(self.residues)
        data['POINTERS'][NRES] = nres
        self.pointers['NRES'] = nres
        data['RESIDUE_LABEL'] = [res.name for res in self.residues]
        data['RESIDUE_POINTER'] = [res.atoms[0].idx+1 for res in self.residues]
        if 'RESIDUE_NUMBER' in data:
            data['RESIDUE_NUMBER'] = [res.number for res in self.residues]
        if 'RESIDUE_CHAINID' in data:
            data['RESIDUE_CHAINID'] = [res.chain for res in self.residues]
        if 'RESIDUE_ICODE' in data:
            data['RESIDUE_ICODE'] = [res.icode for res in self.residues]
        nmxrs = max([len(res) for res in self.residues])
        data['POINTERS'][NMXRS] = nmxrs
        self.pointers['NMXRS'] = nmxrs

    #===================================================

    def _xfer_bond_properties(self):
        """
        Sets the data for the various bond arrays in the raw data from the
        parameter lists
        """
        # First do the bond types
        data = self.parm_data
        for bond_type in self.bond_types:
            bond_type.used = False
        for bond in self.bonds:
            bond.type.used = True
        self.bond_types.prune_unused()
        data['BOND_FORCE_CONSTANT'] = [type.k for type in self.bond_types]
        data['BOND_EQUIL_VALUE'] = [type.req for type in self.bond_types]
        data['POINTERS'][NUMBND] = len(self.bond_types)
        self.pointers['NUMBND'] = len(self.bond_types)
        # Now do the bond arrays
        data['BONDS_INC_HYDROGEN'] = bond_array = []
        for i, bond in enumerate(self.bonds_inc_h):
            bond_array.extend([bond.atom1.idx*3, bond.atom2.idx*3,
                               bond.type.idx+1])
        data['POINTERS'][NBONH] = i + 1
        self.pointers['NBONH'] = i + 1
        data['BONDS_WITHOUT_HYDROGEN'] = bond_array = []
        for i, bond in enumerate(self.bonds_without_h):
            bond_array.extend([bond.atom1.idx*3, bond.atom2.idx*3,
                               bond.type.idx+1])
        data['POINTERS'][MBONA] = data['POINTERS'][NBONA] = i + 1
        self.pointers['MBONA'] = self.pointers['NBONA'] = i + 1

    #===================================================

    def _xfer_angle_properties(self):
        """
        Sets the data for the various angle arrays in the raw data from the
        parameter lists
        """
        # First do the angle types
        data = self.parm_data
        for angle_type in self.angle_types:
            angle_type.used = False
        for angle in self.angles:
            angle.type.used = True
        self.angle_types.prune_unused()
        data['ANGLE_FORCE_CONSTANT'] = [type.k for type in self.angle_types]
        data['ANGLE_EQUIL_VALUE'] = [type.theteq for type in self.angle_types]
        # Now do the angle arrays
        data['ANGLES_INC_HYDROGEN'] = angle_array = []
        for i, angle in enumerate(self.angles_inc_h):
            angle_array.extend([angle.atom1.idx*3, angle.atom2.idx*3,
                                angle.atom3.idx*3, angle.type.idx+1])
        data['POINTERS'][NTHETH] = i + 1
        self.pointers['NTHETH'] = i + 1
        data['ANGLES_WITHOUT_HYDROGEN'] = angle_array = []
        for i, angle in enumerate(self.angles_without_h):
            angle_array.extend([angle.atom1.idx*3, angle.atom2.idx*3,
                                angle.atom3.idx*3, angle.type.idx+1])
        data['POINTERS'][NTHETA] = data['POINTERS'][MTHETA] = i + 1
        self.pointers['NTHETA'] = self.pointers['MTHETA'] = i + 1

    #===================================================

    def _xfer_dihedral_properties(self):
        """
        Sets the data for the various dihedral arrays in the raw data from the
        parameter lists
        """
        # First do the dihedral types
        data = self.parm_data
        for dihedral_type in self.dihedral_types:
            dihedral_type.used = False
        for dihed in self.dihedrals:
            dihed.type.used = True
        self.dihedral_types.prune_unused()
        data['DIHEDRAL_FORCE_CONSTANT'] = [type.phi_k
                for type in self.dihedral_types]
        data['DIHEDRAL_PERIODICITY'] = [type.per
                for type in self.dihedral_types]
        data['DIHEDRAL_PHASE'] = [type.phase for type in self.dihedral_types]
        # Now do the dihedral arrays
        data['DIHEDRALS_INC_HYDROGEN'] = dihed_array = []
        for i, dihed in enumerate(self.dihedrals_inc_h):
            if dihed.atom3.idx == 0 or dihed.atom4.idx == 0:
                dihed_array.extend([dihed.atom4.idx*3, dihed.atom3.idx*3,
                                    dihed.atom2.idx*3, dihed.atom1.idx*3,
                                    dihed.type.idx+1])
            else:
                dihed_array.extend([dihed.atom1.idx*3, dihed.atom2.idx*3,
                                    dihed.atom3.idx*3, dihed.atom4.idx*3,
                                    dihed.type.idx+1])
        data['POINTERS'][NPHIH] = i + 1
        self.pointers['NPHIH'] = i + 1
        data['DIHEDRALS_WITHOUT_HYDROGEN'] = dihed_array = []
        for i, dihed in enumerate(self.dihedrals_without_h):
            if dihed.atom3.idx == 0 or dihed.atom4.idx == 0:
                dihed_array.extend([dihed.atom4.idx*3, dihed.atom3.idx*3,
                                    dihed.atom2.idx*3, dihed.atom1.idx*3,
                                    dihed.type.idx+1])
            else:
                dihed_array.extend([dihed.atom1.idx*3, dihed.atom2.idx*3,
                                    dihed.atom3.idx*3, dihed.atom4.idx*3,
                                    dihed.type.idx+1])
        data['POINTERS'][NPHIA] = data['POINTERS'][MPHIA] = i + 1
        self.pointers['NPHIA'] = self.pointers['MPHIA'] = i + 1

    #===================================================

    def ToMolecule(self):
        """ Translates an amber system into a molecule format """
        from chemistry.molecule import Molecule

        # Remake the topology file if it's changed
        if self.is_changed():
            self.remake_parm()
            if self.ptr('ifbox'): self.rediscover_molecules()
            self.load_structure()

        all_bonds = []        # bond array in Molecule format
        residue_pointers = [] # residue pointers adjusted for indexing from 0
        radii = []

        # Set up initial, blank, bond array
        for i in xrange(self.pointers['NATOM']):
            all_bonds.append([])
      
        # Fill up bond arrays with bond partners excluding H atoms
        for i in xrange(self.pointers['MBONA']):
            atom1 = self.parm_data['BONDS_WITHOUT_HYDROGEN'][3*i  ]//3
            atom2 = self.parm_data['BONDS_WITHOUT_HYDROGEN'][3*i+1]//3
            all_bonds[atom1].append(atom2)
            all_bonds[atom2].append(atom1)

        # Fill up bond arrays with bond partners including H atoms
        for i in xrange(self.pointers['NBONH']):
            atom1 = self.parm_data['BONDS_INC_HYDROGEN'][3*i  ]//3
            atom2 = self.parm_data['BONDS_INC_HYDROGEN'][3*i+1]//3
            all_bonds[atom1].append(atom2)
            all_bonds[atom2].append(atom1)

        # Sort bond arrays
        for i in xrange(len(all_bonds)):
            all_bonds[i].sort()

        # Adjust RESIDUE_POINTER for indexing from 0
        for i in xrange(len(self.parm_data['RESIDUE_POINTER'])):
            residue_pointers.append(self.parm_data['RESIDUE_POINTER'][i]-1)

        # Determine which element each atom is
        elements = [Element[atm.atomic_number] for atm in self.atoms]

        # Put together the title
        title = ''
        try:
            for i in xrange(len(self.parm_data['TITLE'])):
                title += self.parm_data['TITLE'][i]
        except KeyError:
            for i in xrange(len(self.parm_data['CTITLE'])):
                title += self.parm_data['CTITLE'][i]

        # Fill the VDW radii array
        self.fill_LJ()
        for atm in self.atoms:
            radii.append(self.LJ_radius[self.LJ_types[atm.type]-1])
        try:
            return Molecule(atoms=self.parm_data['ATOM_NAME'][:],
                            atom_types=self.parm_data['AMBER_ATOM_TYPE'][:],
                            charges=self.parm_data['CHARGE'][:],
                            residues=self.parm_data['RESIDUE_LABEL'][:],
                            bonds=all_bonds,
                            residue_pointers=residue_pointers,
                            coords=self.coords[:],
                            elements=elements,
                            title=title,
                            radii=radii
            )
        except AttributeError: # use dummy list if no coords are loaded
            return Molecule(atoms=self.parm_data['ATOM_NAME'][:],
                            atom_types=self.parm_data['AMBER_ATOM_TYPE'][:],
                            charges=self.parm_data['CHARGE'][:],
                            residues=self.parm_data['RESIDUE_LABEL'][:], 
                            bonds=all_bonds,
                            residue_pointers=residue_pointers,
                            coords=list(xrange(self.pointers['NATOM']*3)),
                            elements=elements,
                            title=title,
                            radii=radii
            )

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class Rst7(object):
    """
    Amber input coordinate (or restart coordinate) file. Front-end for the
    readers and writers, supports both NetCDF and ASCII restarts.
    """

    def __init__(self, filename=None, natom=None, title='', hasvels=False,
                 hasbox=False, time=0.0):
        """
        Optionally takes a filename to read. This is deprecated, though, as the
        alternative constructor "open" should be used instead
        """
        self.coordinates = []
        self.velocities = []
        self.box = []
        self.hasvels = hasvels
        self.hasbox = hasbox
        self.natom = natom
        self.title = title
        self.time = 0
        if filename is not None:
            self.filename = filename
            warn('Use Rst7.open() constructor instead of default constructor '
                 'to parse restart files.', DeprecationWarning)
            self._read(filename)

    @classmethod
    def open(cls, filename):
        """
        Constructor that opens and parses an input coordinate file
        """
        inst = cls()
        inst.filename = filename
        inst._read(filename)
        return inst

    def _read(self, filename):
        """
        Open and parse an input coordinate file in either ASCII or NetCDF format
        """
        from chemistry.amber.asciicrd import AmberAsciiRestart
        from chemistry.amber.netcdffiles import NetCDFRestart
        try:
            f = AmberAsciiRestart(filename, 'r')
            self.natom = f.natom
        except ValueError:
            # Maybe it's a NetCDF file?
            try:
                f = NetCDFRestart.open_old(filename)
                self.natom = f.atom
            except ImportError:
                raise ReadError('Could not parse %s as an ASCII restart and '
                                'could not find any NetCDF-Python packages to '
                                'attempt to parse as a NetCDF Restart.'
                                % filename)
            except RuntimeError:
                raise ReadError('Could not parse restart file %s' % filename)

        self.coordinates = f.coordinates
        self.hasvels = f.hasvels
        self.hasbox = f.hasbox
        if f.hasvels:
            self.velocities = f.velocities
        if f.hasbox:
            self.box = f.box
        self.title = f.title
        self.time = f.time

    @property
    def coords(self):
        """ Deprecated for coordinates now """
        warn('coords attribute of Rst7 is deprecated. Use coordinates instead',
             DeprecationWarning)
        return self.coordinates
   
    @property
    def vels(self):
        """ Deprecated for velocities now """
        warn('vels attribute of Rst7 is deprecated. Use velocities instead',
             DeprecationWarning)
        return self.velocities

    @classmethod
    def copy_from(cls, thing):
        """
        Copies the coordinates, velocities, and box information from another
        instance
        """
        inst = cls()
        inst.natom = thing.natom
        inst.title = thing.title
        inst.coordinates = thing.coordinates[:]
        inst.hasvels = thing.hasvels
        if hasattr(thing, 'velocities'): inst.velocities = thing.velocities[:]
        inst.hasbox = thing.hasbox
        if hasattr(thing, 'box'): inst.box = thing.box[:]
        inst.time = thing.time

        return inst

    def __copy__(self):
        """ Copy constructor """
        return type(self).copy_from(self)

    def write(self, fname, netcdf=False):
        """ Writes the coordinates and/or velocities to a restart file """
        from chemistry.amber.asciicrd import AmberAsciiRestart
        from chemistry.amber.netcdffiles import NetCDFRestart
        if netcdf:
            if self.natom is None:
                raise RuntimeError('Number of atoms must be set for NetCDF '
                                   'Restart files before write time')
            f = NetCDFRestart.open_new(fname, self.natom, self.hasbox,
                                       self.hasvels, self.title)
        else:
            f = AmberAsciiRestart(fname, 'w', natom=self.natom,
                                  title=self.title)

        f.time = self.time
        # Now write the coordinates
        f.coordinates = self.coordinates
        if self.hasvels:
            f.velocities = self.velocities
        if self.hasbox:
            f.box = self.box
        f.close()

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def set_molecules(parm):
    """
    Correctly sets the ATOMS_PER_MOLECULE and SOLVENT_POINTERS sections of the
    topology file.
    """
    from sys import setrecursionlimit, getrecursionlimit
    # Since we use a recursive function here, we make sure that the recursion
    # limit is large enough to handle the maximum possible recursion depth we'll
    # need (NATOM). We don't want to shrink it, though, since we use list
    # comprehensions in list constructors in some places that have an implicit
    # (shallow) recursion, therefore, reducing the recursion limit too much here
    # could raise a recursion depth exceeded exception during a _Type/Atom/XList
    # creation. Therefore, set the recursion limit to the greater of the current
    # limit or the number of atoms
    setrecursionlimit(max(parm.ptr('natom'), getrecursionlimit()))

    # Unmark all atoms so we can track which molecule each goes into
    parm.atoms.unmark()

    if not parm.ptr('ifbox'):
        raise MoleculeError('Only periodic prmtops can have '
                            'Molecule definitions')
    # The molecule "ownership" list
    owner = []
    # The way I do this is via a recursive algorithm, in which
    # the "set_owner" method is called for each bonded partner an atom
    # has, which in turn calls set_owner for each of its partners and 
    # so on until everything has been assigned.
    molecule_number = 1 # which molecule number we are on
    for i in xrange(parm.ptr('natom')):
        # If this atom has not yet been "owned", make it the next molecule
        # However, we only increment which molecule number we're on if 
        # we actually assigned a new molecule (obviously)
        if not parm.atoms[i].marked:
            tmp = [i]
            _set_owner(parm, tmp, i, molecule_number)
            # Make sure the atom indexes are sorted
            tmp.sort()
            owner.append(tmp)
            molecule_number += 1
    return owner

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def _set_owner(parm, owner_array, atm, mol_id):
    """ Recursively sets ownership of given atom and all bonded partners """
    parm.atoms[atm].marked = mol_id
    for partner in parm.atoms[atm].bond_partners:
        if not partner.marked:
            owner_array.append(partner.idx)
            _set_owner(parm, owner_array, partner.idx, mol_id)
        elif partner.marked != mol_id:
            raise MoleculeError('Atom %d in multiple molecules' % 
                                partner.idx)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def _zeros(length):
    """ Returns an array of zeros of the given length """
    return [0 for i in xrange(length)]
