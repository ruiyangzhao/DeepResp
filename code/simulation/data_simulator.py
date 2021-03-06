import torch
from torch.utils.data import Dataset
import numpy as np
from scipy.ndimage import rotate as rot
import random

class Simulator(Dataset):
    def __init__(self,image, sig, resp_params, TR, SNR, amp, const, isrot = 0, isflip=0):
        # image: image data,
        # sig: respiration data
        # resp_params : paramter of respiration data [sampling rate (Hz), measuretime(sec)]
        # TR : TR (sec)(sampling period of respiration data to reformat into phase errors)
        # SNR: SNR range [min, max]
        # amp: output scale range [min, max]
        # const: scale of phase error to normalize (frequency shifht (Hz) * TE (sec))
        # isrot: rotation angle for image augmentation
        # isflip: probablity to apply horizontal flipping for image augmentation
        
        self.len = image.shape[2]
        self.TR = TR
        self.image_data = image
        self.sig_data = sig
        self.const = const
        self.rand_max = amp[1]
        self.rand_min = amp[0]
        self.sig_size = sig.shape[0]
        self.isrot = isrot
        self.snr_min = SNR[0]
        self.snr_max = SNR[1]
        self.isfilp = isflip
        self.sample_rate = resp_params[0]
        self.max_time = resp_params[1]
        
        self.output_size = image.shape[1]
    def __getitem__(self, index):
        sig_size = self.sig_size
        TR = self.TR
        sample_rate = self.sample_rate
        tmax = self.max_time
        output_size = self.output_size


        #phase error_make
        start_time = (tmax - TR * output_size-1/sample_rate) * random.random()
        amp = self.rand_min+(self.rand_max-self.rand_min) * random.random()
        sig_match = random.randint(0,sig_size-1) # subject of signal
        res_time = np.expand_dims(np.int32(np.round(
            np.linspace(start_time, start_time + TR * output_size, output_size)*sample_rate)),axis=1) # time of signal
        
        temp_sig = np.transpose(self.sig_data[sig_match,res_time],(1,0))
        temp_sig = temp_sig/np.max(np.abs(temp_sig)) * amp
        phase =  np.exp(1j * 2 * np.pi * self.const * temp_sig)
        
        
        img = self.image_data[:,:,index]
        #rotation
        if(self.isrot>0):
            angle = (random.random() - 0.5) * 2 * self.isrot
            img = rot(np.real(img),angle,reshape=False)+rot(np.imag(img),angle,reshape=False)*1j
            
        #flip
        if(random.random() < self.isfilp):
            img = img[:,::-1]
        
        # phase error applying
        temp_k = np.fft.fftshift(np.fft.fft2(img),axes=(0,1)) * phase 

        #SNR
        if(self.snr_max > 0):
            mean_intensity = np.mean(np.abs(img))
            SNR = self.snr_min + (self.snr_max - self.snr_min) * random.random()
            noise_std = mean_intensity / SNR
            temp_k += (np.random.normal(0,noise_std,size=(output_size,output_size)) + 1j* np.random.normal(0,noise_std,size=(output_size,output_size)))*output_size
            
        #split image# into real & imag.
        ref_comp_img = np.fft.ifft2(np.fft.fftshift(temp_k,axes=(0,1)),axes=(0,1))
        ref_comp_img = ref_comp_img/(4*np.std(np.abs(ref_comp_img),axis = (0,1),keepdims = True))
        
        ref_images = np.zeros((2,224,224),dtype=np.float32)
        
        ref_images[0,:,:] = np.real(ref_comp_img)
        ref_images[1,:,:] = np.imag(ref_comp_img)

        return ref_images, temp_sig[0,:]
    
    def __len__(self):
        return self.len