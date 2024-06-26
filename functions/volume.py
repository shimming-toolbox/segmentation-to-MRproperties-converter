#Dependencies
import numpy as np
from functions.label import SegmentationLabel
import nibabel as nib
import scipy.ndimage
from functions.utils.get_dic_values import to_csv_sus, to_csv_relax
import os

# Parent class for the creation of a non-finite biomechanical model of the body
class volume:
    
    def __init__(self, volume):
        # In this version we correct that the output should be the nifti image
        # This way we can attribute the information from nifti files to the class

        self.nifti = volume # This is now directing to a Nifti file
        self.volume = self.nifti.get_fdata()
        self.dimensions = np.array(self.volume.shape) # It is initially a tuple, but it needs to be an array
        self.uniq_labels = np.unique(self.volume)
        self.segmentation_labels = {} 
        self.sus_dist = np.zeros(self.dimensions)
        self.t2star_vol = np.zeros(self.dimensions)
        self.pd_dist = np.zeros(self.dimensions)
        self.deltaB0 = np.zeros(self.dimensions)
        # The dictionary has keys for every id number and each value 
        # is the corresponding SegmentationLabel daughter class

        self.create_labels()
        # This is the Convention Dictionary for labels_id - names - sus_values

        # Creating folders for the code
        if not os.path.exists("output"):
            os.makedirs('output')
        if not os.path.exists('simulation'):
            os.makedirs('simulation')
        if not os.path.exists("data"):
            os.makedirs("data")

        self.magnitude = None
        self.phase = None
        self.real = None
        self.imaginary = None

    def create_labels(self):
       for label_id in self.uniq_labels:
           self.segmentation_labels[label_id] = SegmentationLabel(label_id)

    def create_segmentation_labels(self):

        # The most important labels are:
        # lungs Bone Soft Tissue SpinalCord CSF
        # These are the regions of the body that impact the most
        # For susceptibility valuesfrom bone, fat and soft tissue:
        # https://pfeifer.phas.ubc.ca/refbase/files/Truong-MRI-2002-20-759.pdf
        #
        # We can create an already pre-defined from convention of label_ids

        # In TotalSegmentator this is labeled Spinal Cord, but
        # it really is the Spinal Canal = Spinal Cord + CSF
        # For SC is (GM + WM)/2 = -9.055
        # From Eva's code GM = -9.03 and WM = -9.08
        self.set_label_name(76,"SpinalCanal")
        self.set_label_susceptibility(76,-9.055)
        # IN this branch of the code, we have added labels for the SC
        # We correct the fact that in Total Seg it was Spinal Canal
        self.set_label_name(256, "spinal_cord")
        self.set_label_susceptibility(256,-9.055)
        self.set_label_name(289, "sc_csf")
        self.set_label_susceptibility(289,-9.05)


        # For the lungs we have [9,10,11,12,13]
        for i in [9,10,11,12,13]:
            self.set_label_name(i,'lungs')
            self.set_label_susceptibility(i,0.4)

        # For the bones we have a lot more labels
        # Vertebrae and ribs. But all of them can have the same value: -11.1
        # Vertebrae list goes from Sacrum to C1
        vertebra_list = np.arange(22,48)
        rib_list = np.append(np.arange(89,114),[68,69,70,71,74,75,88])

        # It was -11.1, but now it is -9.0
        for i in vertebra_list:
            self.set_label_name(i,"bone")
            self.set_label_susceptibility(i,-9.0)

        for i in rib_list:
            self.set_label_name(i, "bone")
            self.set_label_susceptibility(i, -9.0)

        # Last but not least is to give susceptibility values to the organs
        # and soft tissue => susceptibility value of water = -9.05

        sus_water_list = [1, 2, 3, 4, 5, 6, 7, 8, 14, 16]

        self.set_label_name(1, "spleen")
        self.set_label_name(2, "kidney") #Right
        self.set_label_name(3, "kidney") # Left
        self.set_label_name(4, "organ") # Gallblader
        self.set_label_name(5, "liver")
        self.set_label_name(6, "organ") #Stomach
        self.set_label_name(7, "gland") # AdrenalGland
        self.set_label_name(8, "gland") # AdrenalGland
        self.set_label_name(14, "esophagus")
        self.set_label_name(15, "trachea")
        self.set_label_name(16, "gland") # Thyroid


        # Susceptibility value of fat = -8.39

        for i in sus_water_list:
            self.set_label_susceptibility(i, -9.05)

        # For trachea, it should have a susceptibilty value closer to air
        self.set_label_susceptibility(15, 0.4)

        # Soft tissue == water
        # Inside of body == fat


        self.set_label_name(0,"air") # Outside of brain
        self.set_label_susceptibility(0,0.35)

        # If label has not been set it can be considered as fat
        # susceptibility of fat label is considering fat and muscle proportion of the body
        # sus of fat is -7.5, muscle is -9.05 and soft tissue is -9.5
        # Assuming that body is 20% fat, 40% muscle and 40% soft tissue
        # The weighted average of the fat label should be: -8.92

        self.set_label_name(264,"fat")
        self.set_label_susceptibility(264,-8.92)

        # For simulating GRE acquisition we need to set name of organs
        # brain, liver, spleen, kidney
        self.set_label_name(87, "brain")
        self.set_label_name(48,"heart")


        # The other labels missing without names follow

        intestines = [17,18,19,20,21,22,23]
        # small intestine duodenum colon urinary bladder prostate kidney cyst left and right
        for i in intestines:
            self.set_label_name(i,"organ")
            self.set_label_susceptibility(i,-9.05)

        # Lastly if everything was labeled properly what's left are veins and muscles
        # The susceptibility of csf and water is -9.05, of muscle is -9.03 we can combine them
        for i in self.uniq_labels:
            if self.segmentation_labels[i].name == None:
                self.set_label_name(i,"extra")
                self.set_label_susceptibility(i,-9.04)

        # This way we should have everything labeled
    def check_labels(self):
        for i in self.uniq_labels:
            if self.segmentation_labels[i].name == None:
                print("Label: ",self.segmentation_labels[i]["name"]," doesn't have name assigned")

    def set_label_name(self, label_id, name):
        if label_id in self.uniq_labels:
            self.segmentation_labels[label_id].set_name(name)
        else: print(f"Label ID {label_id} not found.")

    def set_label_susceptibility(self, label_id, susceptibility):
        if label_id in self.uniq_labels:
            # SImilar to set_label_name
            self.segmentation_labels[label_id].set_susceptibility(susceptibility)
        else: print(f"Label ID {label_id} not found.")
    def set_label_pd(self,label_id,pd):
        if label_id in self.uniq_labels:
            self.segmentation_labels[label_id].set_pd_val(pd)
        else: print(f"Label ID {label_id} not found.")

    def set_T2star(self, label_id, t2star):
        if label_id in self.uniq_labels:
        # SImilar to set_label_name
            self.segmentation_labels[label_id].set_t2star_val(t2star)
        else:
            print(f"Label ID {label_id} not found.")
 
    def display(self):
        show_slices(self.volume)


    def manual_label(self,id,name,sus):
        if id in self.uniq_labels:
            label = self.segmentation_labels[id]
            label.name = name
            label.sus = sus

    def show_labels(self):
        for i in self.segmentation_labels:
            label = self.segmentation_labels[i]
            print(label) # Calling __str__ from label


    def create_sus_dist(self):
        # Code for create a susceptibility distribution volume
        # Using the label class
        for i in range(self.dimensions[0]):
            for j in range(self.dimensions[1]):
                for k in range(self.dimensions[2]):

                    pixel = self.volume[i,j,k]
                    label = self.segmentation_labels[pixel]
                    suscep = label.susceptibility

                    if suscep == None:
                        # THis means the label is not defined
                        # The only not defined labels are organs
                        # We can consider the suscp of water
                        self.sus_dist[i,j,k] = -9.05
                    else:
                        self.sus_dist[i,j,k] = suscep

        return self.sus_dist

    def save_sus_dist_nii(self):
        # Method to save the susceptibility distribution created to nifti
        temp_img = nib.Nifti1Image(self.sus_dist, affine=self.nifti.affine)
        path = os.path.join('output','sus_dist.nii.gz')
        # Save the new NIfTI image to a file
        nib.save(temp_img,path)
        del temp_img
        del path

    def create_pd_vol(self):
        # This method will use the lookup table of PD values to create a new volume
        # This new volume will use the labels to quickly create a volume with ProtonDensity values

        for i in range(self.dimensions[0]):
            for j in range(self.dimensions[1]):
                for k in range(self.dimensions[2]):

                    pixel = self.volume[i,j,k]
                    label = self.segmentation_labels[pixel]
                    pd = label.PD_val
                    if pd == None:
                        # THis means the label does not have PD defined
                        self.pd_dist[i,j,k] = 0
                    else:
                        # If the label has PD value it will put this value on the volume
                        self.pd_dist[i,j,k] = pd

        return self.pd_dist
    def save_pd_dist(self):
        # Method to save the proton density distribution created to nifti
        temp_img = nib.Nifti1Image(self.pd_dist, affine=self.nifti.affine)
        # Save the new NIfTI image to a file
        path = os.path.join('output', 'pd_dist.nii.gz')
        nib.save(temp_img,path)
        del temp_img
        del path
    def create_t2_star_vol(self):
        # This method will use the lookup table of T2 star values to create a new volume
        # This new volume will use the labels to quickly create a volume with relaxation time
        for i in range(self.dimensions[0]):
            for j in range(self.dimensions[1]):
                for k in range(self.dimensions[2]):

                    pixel = self.volume[i,j,k]
                    label = self.segmentation_labels[pixel]
                    t2star = label.T2star_val
                    if t2star == None:
                        # THis means the label does not have T2 star value defined
                        self.t2star_vol[i,j,k] = 0.001
                    else:
                        # If the label has value it will put this value on the volume
                        self.t2star_vol[i,j,k] = t2star

        return self.t2star_vol
    def save_t2star_dist(self):
        # Method to save the proton density distribution created to nifti
        temp_img = nib.Nifti1Image(self.t2star_vol, affine=self.nifti.affine)
        # Save the new NIfTI image to a file
        path = os.path.join('output', 't2_star.nii.gz')
        nib.save(temp_img,path)
        del temp_img
        del path
    def save_sus_csv(self):
        data = []
        for i in self.segmentation_labels.keys():
            label = self.segmentation_labels[i]
            if label.name is not None and label.susceptibility is not None and label.name not in data:
                # The last is to get unique names 
                data.append({
                    "Name": label.name,
                    "Susceptibility": label.susceptibility
                })
        # Call funtion that creates CSV
        path = os.path.join('data','susceptibility_values.csv')
        to_csv_sus(data,path)

    def save_relax_csv(self):
        # Further implementation to go through self.relax values of each label?
        # Think about a more efficient way because the user should be able to change the values
        # It might be usefull to get this inputs from different researchers and testing
        pass
    def __repr__(self):
        return f"SegmentationLabelManager == Volume"
