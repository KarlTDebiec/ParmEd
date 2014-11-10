"""
Unittests for the classes and interfaces defined in chemistry.topologyobjects

By Jason Swails
"""
from __future__ import division

from chemistry.exceptions import (BondError, DihedralError, CmapError,
                                  AmoebaError)
from chemistry.topologyobjects import _ListItem, _FourAtomTerm
from chemistry.topologyobjects import *
import unittest
import random

class TestTopologyObjects(unittest.TestCase):
    """
    This test set is responsible for testing the classes in
    chemistry.topologyobjects
    """

    #=============================================

    def test_list_item1(self):
        """ Test the _ListItem base class in standard containers """
        my_container = list()
        objects = [_ListItem() for i in range(100)]
        # Assign it a list container
        for obj in objects:
            obj.list = my_container
            my_container.append(obj)
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)
        # Delete 10 random, but unique, objects from my_container
        choices = set()
        while len(choices) < 10:
            choices.add(random.choice(range(100)))
        choices = sorted(list(choices), reverse=True)
        for idx in choices:
            my_container.pop(idx)
        # Now check that the index of those 10 items are -1
        for i in choices:
            self.assertEqual(objects[i].idx, -1)
        # Now check that the index of the remaining objects are correctly
        # updated
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)

    #=============================================

    def test_list_item2(self):
        """ Test the _ListItem base class in the TrackedList container """
        my_container = TrackedList()
        objects = [_ListItem() for i in range(100)]
        # Assign it a list container
        for obj in objects:
            obj.list = my_container
            my_container.append(obj)
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)
        # Delete 10 random, but unique, objects from my_container
        choices = set()
        while len(choices) < 10:
            choices.add(random.choice(range(100)))
        choices = sorted(list(choices), reverse=True)
        for idx in choices:
            my_container.pop(idx)
        # Now check that the index of those 10 items are -1
        for i in choices:
            self.assertEqual(objects[i].idx, -1)
        # Now check that the index of the remaining objects are correctly
        # updated
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)
        # Now add those 10 objects back to the end of the list, and make sure
        # that the indexing is still correct, then delete those same items using
        # "del" instead of "pop" and make sure it still works
        for i in choices:
            my_container.append(objects[i])
        objects = [obj for obj in my_container] # Re-sync ordering
        for i in choices:
            del my_container[i]
        for i in choices:
            self.assertEqual(objects[i].idx, -1)
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)
        # Now try deleting a slice
        objects = [obj for obj in my_container]
        del my_container[::2]
        self.assertEqual(len(my_container), 45)
        for i in range(90):
            if i % 2 == 0:
                self.assertEqual(objects[i].idx, -1)
            else:
                self.assertEqual(objects[i].idx, i//2)
        for i, obj in enumerate(my_container):
            self.assertEqual(obj.idx, i)

    #=============================================

    def test_four_atom_term(self):
        """ Tests the _FourAtomTerm base class """
        a1, a2, a3, a4, a5 = Atom(), Atom(), Atom(), Atom(), Atom()
        fat = _FourAtomTerm(a1, a2, a3, a4)
        # Verify ordering
        self.assertIs(fat.atom1, a1)
        self.assertIs(fat.atom2, a2)
        self.assertIs(fat.atom3, a3)
        self.assertIs(fat.atom4, a4)
        # Verify container
        self.assertIn(a1, fat)
        self.assertIn(a2, fat)
        self.assertIn(a3, fat)
        self.assertIn(a4, fat)
        self.assertNotIn(a5, fat)

    #=============================================

    def test_atom(self):
        """ Tests the Atom object """
        a1 = Atom(atomic_number=6, name='C1', type='CT', charge=-0.1,
                  mass=12.01, nb_idx=1, radii=1.8, tree='M')
        a2 = Atom(atomic_number=6, name='C2', type='CT', charge=0.1,
                  mass=12.01, nb_idx=1, radii=1.8, tree='M')
        a3 = Atom(atomic_number=6, name='C3', type='CT', charge=0.0,
                  mass=12.01, nb_idx=1, radii=1.8, tree='M')
        a4 = Atom(atomic_number=6, name='C4', type='CT', charge=-0.1,
                  mass=12.01, nb_idx=1, radii=1.8, tree='M')
        a5 = Atom(atomic_number=6, name='C2', type='CT', charge=0.1,
                  mass=12.01, nb_idx=1, radii=1.8, tree='M')
        # Make sure the atom attributes are transferred correctly (only check
        # the first atom)
        self.assertEqual(a1.atomic_number, 6)
        self.assertEqual(a1.element, 6)
        self.assertEqual(a1.name, 'C1')
        self.assertEqual(a1.type, 'CT')
        self.assertEqual(a1.charge, -0.1)
        self.assertEqual(a1.mass, 12.01)
        self.assertEqual(a1.tree, 'M')
        self.assertEqual(a1.nb_idx, 1)
        self.assertEqual(a1.radii, 1.8)
        self.assertEqual(a1.idx, -1)
        self.assertEqual(a1.marked, 0)
        self.assertEqual(a1.screen, 0)

        bonds = list()
        angles = list()
        torsions = list()
        tortors = list()
        bonds.append(Bond(a1, a2))
        bonds.append(Bond(a2, a3))
        bonds.append(Bond(a3, a4))
        bonds.append(Bond(a4, a5))
        angles.append(Angle(a1, a2, a3))
        angles.append(Angle(a2, a3, a4))
        angles.append(Angle(a3, a4, a5))
        torsions.append(Dihedral(a1, a2, a3, a4))
        torsions.append(Dihedral(a2, a3, a4, a5))
        tortors.append(TorsionTorsion(a1, a2, a3, a4, a5))

        self.assertIn(a1, bonds[0])
        self.assertNotIn(a1, bonds[1])
        self.assertIn(a1, angles[0])
        self.assertNotIn(a1, angles[1])
        self.assertIn(a1, torsions[0])
        self.assertNotIn(a1, torsions[1])
        self.assertIn(a1, tortors[0])

        self.assertIn(bonds[0], a1.bonds)
        self.assertIn(bonds[0], a2.bonds)
        self.assertIn(bonds[1], a2.bonds)
        self.assertIn(bonds[1], a3.bonds)

        self.assertIn(angles[0], a1.angles)
        self.assertIn(angles[0], a2.angles)
        self.assertIn(angles[1], a2.angles)
        self.assertIn(angles[0], a3.angles)
        self.assertIn(angles[1], a3.angles)
        self.assertIn(angles[2], a3.angles)

        self.assertIn(torsions[0], a1.dihedrals)
        self.assertIn(torsions[0], a2.dihedrals)
        self.assertIn(torsions[0], a3.dihedrals)
        self.assertIn(torsions[0], a4.dihedrals)
        self.assertNotIn(torsions[0], a5.dihedrals)
        self.assertNotIn(torsions[1], a1.dihedrals)
        self.assertIn(torsions[1], a2.dihedrals)
        self.assertIn(torsions[1], a3.dihedrals)
        self.assertIn(torsions[1], a4.dihedrals)
        self.assertIn(torsions[1], a5.dihedrals)

        self.assertIn(tortors[0], a1.tortors)
        self.assertIn(tortors[0], a2.tortors)
        self.assertIn(tortors[0], a3.tortors)
        self.assertIn(tortors[0], a4.tortors)
        self.assertIn(tortors[0], a5.tortors)

        self.assertIn(a1, a2.bond_partners)
        self.assertIn(a2, a1.bond_partners)
        # Those in bond partners should not be in other partners
        self.assertNotIn(a1, a2.angle_partners)
        self.assertNotIn(a1, a2.dihedral_partners)

        self.assertIn(a1, a3.angle_partners)
        self.assertIn(a3, a1.angle_partners)
        self.assertNotIn(a1, a3.dihedral_partners)
        self.assertNotIn(a1, a3.bond_partners)
        self.assertIn(a1, a4.dihedral_partners)

        # Test it in a list
        atoms = [a1, a2, a3, a4, a5]
        for i, atom in enumerate(atoms):
            atom.list = atoms
            self.assertEqual(atom.idx, i)

    #=============================================

    def test_bond(self):
        """ Tests the Bond and BondType classes """
        a1, a2, a3, a4 = Atom(), Atom(), Atom(), Atom()
        bond = Bond(a1, a2)
        # Test Bond as a container
        self.assertIn(a1, bond)
        self.assertIn(a2, bond)
        self.assertNotIn(a3, bond)
        self.assertNotIn(a4, bond)
        self.assertIn(bond, a1.bonds)
        self.assertIn(bond, a2.bonds)
        # Delete the bond and make sure it is deleted from the atoms, too
        bond.delete()
        self.assertEqual(len(a1.bonds), 0)
        self.assertNotIn(bond, a1.bonds)
        self.assertNotIn(a2, a1.bonds)
        self.assertNotIn(a1, a2.bonds)
        # Add multiple bonds
        bond1 = Bond(a1, a2)
        bond2 = Bond(a2, a3)
        bond3 = Bond(a3, a4)
        bond4 = Bond(a1, a2) # Duplicate
        bond1.delete()
        self.assertIn(a1, a2.bond_partners) # Duplicated bond
        bond4.delete()
        self.assertNotIn(a1, a2.bond_partners)
        # Now test the bond types
        bond_types = TrackedList()
        bond_types.append(BondType(10.0, 1.0, bond_types))
        bond_types.append(BondType(12.0, 1.1, bond_types))
        bond_types.append(BondType(10.0, 1.0, bond_types))
        bond1 = Bond(a1, a2, bond_types[0])
        bond4 = Bond(a1, a2, bond_types[0])
        bond2.type = bond_types[1]
        bond3.type = bond_types[2]
        self.assertIs(bond1.type, bond4.type)
        self.assertIsNot(bond1.type, bond3.type)
        self.assertEqual(bond1.type, bond3.type)
        self.assertEqual(bond1.type.idx, 0)
        self.assertEqual(bond4.type.idx, 0)
        self.assertEqual(bond2.type.idx, 1)
        self.assertEqual(bond3.type.idx, 2)
        self.assertIs(bond1.type.list, bond_types)

    #=============================================

    def test_angle(self):
        """ Tests the Angle and AngleType classes """
        a1, a2, a3, a4 = Atom(), Atom(), Atom(), Atom()
        b1 = Bond(a1, a2)
        b2 = Bond(a2, a3)
        b3 = Bond(a3, a4)
        b4 = Bond(a4, a2)
        ang1 = Angle(a1, a2, a3)
        ang2 = Angle(a2, a3, a4)
        angle_types = TrackedList()
        # Make a set of angle types
        angle_types.append(AngleType(50.0, 109.5, angle_types))
        angle_types.append(AngleType(30.0, 120.0, angle_types))
        angle_types.append(AngleType(50.0, 109.5, angle_types))
        # Assign the angle types to the angles (assigning to one new one)
        ang3 = Angle(a3, a4, a2, angle_types[2])
        ang1.type = angle_types[0]
        ang2.type = angle_types[1]
        # Test angle as a container
        self.assertIn(a1, ang1)
        self.assertIn(a2, ang1)
        self.assertIn(a3, ang1)
        self.assertNotIn(a4, ang1)
        self.assertIn(b1, ang1)
        self.assertIn(b2, ang1)
        self.assertNotIn(b3, ang1)
        self.assertIn(b2, ang2)
        self.assertIn(b3, ang2)
        self.assertNotIn(b4, ang2)
        # Check that this angle is properly registered in each atom, and that
        # two atoms are not both angle and bond partners
        self.assertIn(a2, a1.bond_partners)
        self.assertIn(a3, a1.angle_partners)
        self.assertIn(a3, a2.bond_partners)
        self.assertNotIn(a2, a1.angle_partners)
        self.assertIn(ang1, a1.angles)
        self.assertIn(ang1, a2.angles)
        self.assertIn(ang1, a3.angles)
        self.assertIn(ang2, a2.angles)
        # Now check the types
        self.assertIs(ang1.type, angle_types[0])
        self.assertIsNot(ang3.type, ang1.type)
        self.assertEqual(ang3.type, ang1.type)
        self.assertNotEqual(ang1.type, ang2.type)
        self.assertEqual(angle_types[0].idx, 0)
        self.assertEqual(angle_types[1].idx, 1)
        self.assertEqual(angle_types[2].idx, 2)

    #=============================================

    def test_dihedral(self):
        """ Tests the Dihedral and DihedralType classes """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for i in range(10)])
        bonds = []
        # Sequential bonds
        for i in range(len(atoms)-2):
            bonds.append(Bond(atoms[i], atoms[i+1]))
        bonds.append(Bond(atoms[-1], atoms[1])) # to make an improper
        bonds.append(Bond(atoms[0], atoms[-1])) # stupid bond
        dihed_types = TrackedList()
        dihed_types.append(DihedralType(5.0, 2, 0.0, 1.2, 2.0, dihed_types))
        dihed_types.append(DihedralType(1.0, 3, 180.0, 1.2, 2.0, dihed_types))
        dihed_types.append(DihedralType(2.0, 4, 180.0, 1.2, 2.0, dihed_types))
        dihed_types.append(DihedralType(10.0, 1, 180.0, 0., 0., dihed_types))
        d1 = Dihedral(atoms[0], atoms[-1], atoms[1], atoms[2], improper=True,
                      type=dihed_types[3])
        d2 = Dihedral(atoms[0], atoms[1], atoms[2], atoms[3],
                      type=dihed_types[0])
        d3 = Dihedral(atoms[0], atoms[1], atoms[2], atoms[3], ignore_end=True,
                      type=dihed_types[1])
        d4 = Dihedral(atoms[1], atoms[2], atoms[3], atoms[4],
                      type=dihed_types[2])
        # Test container properties
        self.assertIn(bonds[-2], d1)
        self.assertIn(bonds[0], d1)
        self.assertIn(bonds[1], d1)
        self.assertNotIn(bonds[-1], d1)
        self.assertIn(bonds[0], d2)
        self.assertIn(bonds[1], d2)
        self.assertIn(bonds[2], d2)
        self.assertNotIn(bonds[3], d2)
        for i, a in enumerate(atoms):
            if i < 4:
                self.assertIn(a, d2)
                self.assertIn(a, d3)
                if i > 0:
                    self.assertIn(a, d4)
                else:
                    self.assertNotIn(a, d4)
            else:
                if i == 4:
                    self.assertIn(a, d4)
                else:
                    self.assertNotIn(a, d4)
                self.assertNotIn(a, d2)
                self.assertNotIn(a, d3)
        # Check the various attributes of the different dihedrals
        self.assertTrue(d1.improper and d1.ignore_end)
        self.assertTrue(d3.ignore_end and not d3.improper)
        self.assertFalse(d2.ignore_end or d2.improper)
        self.assertFalse(d4.ignore_end or d4.improper)
        self.assertEqual(d1.signs, [-1, -1])
        self.assertEqual(d2.signs, [1, 1])
        self.assertEqual(d3.signs, [-1, 1])
        self.assertEqual(d4.signs, [1, 1])
        self.assertEqual(d1.type.idx, 3)
        self.assertEqual(d2.type.idx, 0)
        self.assertEqual(d3.type.idx, 1)
        self.assertEqual(d4.type.idx, 2)
        self.assertEqual(d1.type.phi_k, 10.0)
        self.assertEqual(d1.type.per, 1)
        self.assertEqual(d1.type.phase, 180)
        self.assertEqual(d1.type.scee, 0.)
        self.assertEqual(d1.type.scnb, 0.)

        self.assertTrue(d1.same_atoms((0, 9, 1, 2)))
        self.assertFalse(d1.same_atoms((0, 1, 9, 2)))
        self.assertTrue(d1.same_atoms(d1))
        self.assertFalse(d1.same_atoms(d2))
        self.assertTrue(d2.same_atoms((0, 1, 2, 3)))
        self.assertTrue(d2.same_atoms((3, 2, 1, 0)))
        self.assertFalse(d2.same_atoms((2, 3, 1, 0)))
        self.assertNotIn(atoms[0], atoms[1].dihedral_partners)
        d2.delete()
        self.assertIn(atoms[0], atoms[3].dihedral_partners)
        self.assertIn(atoms[3], atoms[0].dihedral_partners)
        d3.delete()
        self.assertNotIn(atoms[0], atoms[3].dihedral_partners)
        self.assertNotIn(atoms[3], atoms[0].dihedral_partners)

    #=============================================

    def test_urey_bradley(self):
        """ Tests the Urey-Bradley term """
        atoms = TrackedList()
        atoms.extend([Atom(), Atom(), Atom()])
        b1 = Bond(atoms[0], atoms[1])
        b2 = Bond(atoms[1], atoms[2])
        b3 = Bond(atoms[0], atoms[2])
        a1 = Angle(atoms[0], atoms[1], atoms[2])
        u1 = UreyBradley(atoms[0], atoms[2], BondType(10.0, 1.0))
        # Test containers
        self.assertIn(atoms[0], u1)
        self.assertIn(atoms[2], u1)
        self.assertNotIn(atoms[1], u1)
        self.assertIn(b1, u1)
        self.assertIn(b2, u1)
        self.assertNotIn(b3, u1)
        self.assertEqual(u1.type.k, 10)
        self.assertEqual(u1.type.req, 1)

    #=============================================

    def test_improper(self):
        """ Tests the CHARMM improper torsion term and type """
        atoms = TrackedList([Atom(), Atom(), Atom(), Atom()])
        for atom in atoms: atom.list = atoms
        b1 = Bond(atoms[0], atoms[1])
        b2 = Bond(atoms[0], atoms[2])
        b3 = Bond(atoms[0], atoms[3])
        imp_types = TrackedList()
        imp_types.append(ImproperType(10.0, 180.0, list=imp_types))
        imp_types.append(ImproperType(10.0, 180.0, list=imp_types))
        imp = Improper(atoms[0], atoms[1], atoms[2], atoms[3], imp_types[0])
        imp2 = Improper(atoms[0], atoms[3], atoms[1], atoms[2], imp_types[1])
        for a in atoms:
            self.assertIn(a, imp)
        self.assertEqual(imp.type.idx, 0)
        self.assertEqual(imp.type.psi_k, 10.0)
        self.assertEqual(imp.type.psi_eq, 180.0)
        self.assertTrue(imp.same_atoms((0, 1, 2, 3)))
        self.assertTrue(imp.same_atoms((0, 2, 3, 1)))
        self.assertFalse(imp.same_atoms((3, 2, 1, 0)))
        self.assertTrue(imp.same_atoms(imp2))
        self.assertTrue(imp.same_atoms(imp))

    #=============================================

    def test_cmap(self):
        """ Tests the coupled-torsion CMAP terms used by CHARMM """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for i in range(10)])
        bonds = [Bond(atoms[i], atoms[i+1]) for i in range(9)]
        cg1 = list(range(36))
        cg2 = list(reversed(range(36)))
        cmap_types = TrackedList()
        cmap_types.append(CmapType(6, cg1, list=cmap_types))
        cmap_types.append(CmapType(6, cg2, list=cmap_types))
        cmap_types.append(CmapType(6, cg1[:], list=cmap_types))
        cmap1 = Cmap(atoms[0], atoms[1], atoms[2], atoms[3], atoms[4],
                     cmap_types[0])
        cmap2 = Cmap(atoms[3], atoms[4], atoms[5], atoms[6], atoms[7],
                     cmap_types[1])
        cmap3 = Cmap(atoms[5], atoms[6], atoms[7], atoms[8], atoms[9],
                     cmap_types[2])
        # Check illegal CmapType assignment
        self.assertRaises(CmapError, lambda: CmapType(5, cg1))
        # Check container functionality
        for i, atom in enumerate(atoms):
            if 0 <= i < 5:
                self.assertIn(atom, cmap1)
            if 3 <= i < 7:
                self.assertIn(atom, cmap2)
            if 5 <= i < 9:
                self.assertIn(atom, cmap3)
        self.assertEqual(cmap_types[0], cmap_types[2])
        self.assertNotEqual(cmap_types[0], cmap_types[1])
        for i, bond in enumerate(bonds):
            if 0 <= i < 4:
                self.assertIn(bond, cmap1)
            if 3 <= i < 7:
                self.assertIn(bond, cmap2)
            if 5 <= i < 9:
                self.assertIn(bond, cmap3)
        # Check the same_atoms method
        self.assertTrue(cmap1.same_atoms(cmap1))
        self.assertFalse(cmap2.same_atoms(cmap1))
        self.assertTrue(cmap1.same_atoms((0, 1, 2, 3, 4)))
        self.assertTrue(cmap1.same_atoms((4, 3, 2, 1, 0)))
        self.assertFalse(cmap1.same_atoms((0, 2, 1, 3, 4)))
        # Check Cmap grid indexing
        for i, val in enumerate(cg1):
            self.assertEqual(cmap_types[0].grid[i], val)
            i1 = i // 6
            i2 = i % 6
            self.assertEqual(cmap_types[0].grid[i1,i2], val)
        transpose = cmap_types[0].grid.T
        for i, val in enumerate(cg1):
            i1 = i // 6
            i2 = i % 6
            self.assertEqual(transpose[i2, i1], val)
        # Transpose of the transpose should be the original
        self.assertEqual(transpose.T, cmap_types[0].grid)
        # Check switch_range functionality
        sg = cmap_types[0].grid.switch_range()
        for i in range(6):
            for j in range(6):
                self.assertEqual(sg[i,j], cmap_types[0].grid[(i+3)%6,(j+3)%6])

    #=============================================

    def test_trigonal_angle(self):
        """ Tests the trigonal angle term used in the AMOEBA force field """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for x in range(8)])
        bonds = []
        bonds.append(Bond(atoms[0], atoms[1]))
        bonds.append(Bond(atoms[2], atoms[1]))
        bonds.append(Bond(atoms[3], atoms[1]))
        bonds.append(Bond(atoms[0], atoms[2]))
        t1 = TrigonalAngle(atoms[0], atoms[1], atoms[2], atoms[3])
        t2 = TrigonalAngle(atoms[4], atoms[5], atoms[6], atoms[7],
                           AngleType(50.0, 90.0))
        t1.type = AngleType(50.0, 90.0)
        self.assertIsNot(t1.type, t2.type)
        self.assertEqual(t1.type, t2.type)
        self.assertIn(bonds[0], t1)
        self.assertIn(bonds[1], t1)
        self.assertIn(bonds[2], t1)
        self.assertNotIn(bonds[3], t1)
        self.assertRaises(BondError, lambda: TrigonalAngle(atoms[0], atoms[1],
                                                           atoms[2], atoms[1]))
        self.assertEqual(t1.type.k, 50)
        self.assertEqual(t1.type.theteq, 90.0)

    #=============================================

    def test_oopbend_angle(self):
        """ Tests the out-of-plane bend term used in the AMOEBA force field """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for x in range(8)])
        bonds = []
        bonds.append(Bond(atoms[0], atoms[1]))
        bonds.append(Bond(atoms[2], atoms[1]))
        bonds.append(Bond(atoms[3], atoms[1]))
        bonds.append(Bond(atoms[0], atoms[2]))
        t1 = OutOfPlaneBend(atoms[0], atoms[1], atoms[2], atoms[3])
        t2 = OutOfPlaneBend(atoms[4], atoms[5], atoms[6], atoms[7],
                            AngleType(50.0, 90.0))
        t1.type = AngleType(50.0, 90.0)
        self.assertIsNot(t1.type, t2.type)
        self.assertEqual(t1.type, t2.type)
        self.assertIn(bonds[0], t1)
        self.assertIn(bonds[1], t1)
        self.assertIn(bonds[2], t1)
        self.assertNotIn(bonds[3], t1)
        self.assertRaises(BondError, lambda: TrigonalAngle(atoms[0], atoms[1],
                                                           atoms[2], atoms[1]))
        self.assertEqual(t1.type.k, 50)
        self.assertEqual(t1.type.theteq, 90.0)

    #=============================================

    def test_pitorsion(self):
        """ Tests the pi-torsion term used in the AMOEBA force field """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for i in range(6)])
        bonds = [Bond(atoms[0], atoms[2]), Bond(atoms[1], atoms[2]),
                 Bond(atoms[2], atoms[3]), Bond(atoms[3], atoms[4]),
                 Bond(atoms[3], atoms[5])]
        pit = PiTorsion(*atoms, type=DihedralType(10.0, 2, 180.0))
        for atom in atoms:
            self.assertIn(atom, pit)
        for bond in bonds:
            self.assertIn(bond, pit)
        self.assertNotIn(Bond(atoms[0], atoms[1]), pit)
        self.assertEqual(pit.type.phi_k, 10)
        self.assertEqual(pit.type.per, 2)
        self.assertEqual(pit.type.phase, 180)

    #=============================================

    def test_stretchbend(self):
        """ Tests the stretch-bend term and type """
        atoms = TrackedList()
        atoms.extend([Atom(list=atoms) for i in range(3)])
        bonds = [Bond(atoms[0], atoms[1]), Bond(atoms[1], atoms[2])]
        strbnd = StretchBend(atoms[0], atoms[1], atoms[2],
                             StretchBendType(10.0, 1.1, 1.2, 109.0))
        for obj in atoms + bonds:
            self.assertIn(obj, strbnd)
        self.assertEqual(strbnd.type.idx, -1)
        self.assertEqual(strbnd.type.req1, 1.1)
        self.assertEqual(strbnd.type.req2, 1.2)
        self.assertEqual(strbnd.type.theteq, 109.0)
