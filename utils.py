import numpy as np
from scipy.stats import multivariate_normal
import torch.utils.data as data
import glob,os
from xml_utils import *

def get_gaussian_gt(pose_2d,sigma,img_h,img_w, l_pad = 1.8, r_pad = 1.8, h_pad = 5):
	y1 = np.min(pose_2d[:,1])
	x1 = -l_pad
	x2 = r_pad
	y2 = y1 + h_pad
	x_line = np.linspace(x1,x2,img_w, endpoint = True)
	y_line = np.linspace(y1,y2,img_h, endpoint = True)
	x_mesh,y_mesh = np.meshgrid(x_line,y_line)
	pos = np.empty(x_mesh.shape+ (2,))
	pos[:,:,0] = x_mesh
	pos[:,:,1] = y_mesh
	joint_num = pose_2d.shape[0]
	gt_map = np.zeros((img_h,img_w,joint_num))
	for i in range(joint_num):
		pdf = multivariate_normal(pose_2d[i,:], [[sigma, 0], [0, sigma]])
		gt_map[:,:,i] = np.reshape(pdf.pdf(pos),[img_h,img_w])
	return gt_map

def get_gaussian_gt_3d(pose_3d,sigma, grid_point = 32,pad_space = 1):
	z1 = np.min(pose_3d[:,2])
	z2 = y1 + pad_space * 2
	x1 = -pad_space
	x2 = pad_space
	y1 = -pad_space
	y2 = pad_space

	x_line = np.linspace(x1,x2,grid_point, endpoint = True)
	y_line = np.linspace(y1,y2,grid_point, endpoint = True)
	z_line = np.linspace(z1,z2,grid_point, endpoint = True)
	x_mesh,y_mesh,z_mesh = np.meshgrid(x_line,y_line,z_line)
	pos = np.empty(x_mesh.shape+ (3,))
	pos[:,:,0] = x_mesh
	pos[:,:,1] = y_mesh
	pos[:,:,2] = z_mesh
	joint_num = pose_3d.shape[0]
	gt_map = np.zeros((grid_point,grid_point,grid_point))

	for i in range(joint_num):
		pdf = multivariate_normal(pose_3d[i,:], [[sigma, 0,0], [0,sigma,0], [0, 0, sigma]])
		gt_map += np.reshape(pdf.pdf(pos),[grid_point,grid_point,grid_point])
	return gt_map

class Pose_Dataset(data.Dataset):

	def __init__(self, xml_folder, chunck_size, player_list, total_folder, sigma, img_h, img_w, epoch, reverse_player = True, joint_num = 18):
		self.xml_folder = xml_folder
		self.counter = 0
		self.player_list = player_list
		self.folder_counter = 0
		self.total_folder = total_folder
		self.current_folder_file_num = 0
		self.chunck_size = chunck_size
		self.total_data_num = 0
		self.xml_folder = xml_folder
		self.reverse_player = reverse_player
		self.do_reverse_player = False
		self.joint_num = joint_num
		self.sigma = sigma
		self.h = img_h
		self.w = img_w
		self.epoch = epoch
		for i in range(total_folder):
			player_1_id = self.player_list[i][0]
			player_2_id = self.player_list[i][1]
			self.total_data_num += len(glob.glob(os.path.join\
						(self.xml_folder,'Boxing_p'+str(player_1_id)+'&p'+str(player_2_id),'Skeleton','*.xml')))-chunck_size			

	def __getitem__(self, index):

		if self.current_folder_file_num <= self.chunck_size + self.counter :
			if ~self.do_reverse_player:
				self.player_1_id = self.player_list[self.folder_counter][0]
				self.player_2_id = self.player_list[self.folder_counter][1]
				self.current_folder_name = 'Boxing_p'+str(self.player_1_id)+'&p'+str(self.player_2_id)
			else:
				self.player_1_id = self.player_list[self.folder_counter][1]
				self.player_2_id = self.player_list[self.folder_counter][0]
				self.current_folder_name = 'Boxing_p'+str(self.player_2_id)+'&p'+str(self.player_1_id)
			self.current_folder_file_num = len(glob.glob(os.path.join\
						(self.xml_folder,self.current_folder_name,'Skeleton','*.xml')))
			self.counter = 0
			if self.folder_counter == self.total_folder - 1:
				self.folder_counter = 0
				if self.reverse_player:
					self.do_reverse_player = ~self.do_reverse_player
			else:
				self.folder_counter += 1

		pose_p1 = np.zeros((self.chunck_size,self.joint_num,3))
		pose_p2 = np.zeros((self.chunck_size, self.h, self.w, self.joint_num))
		
		for i in range(self.chunck_size):
			p1,p2 = xml_parsing(os.path.join(self.xml_folder, self.current_folder_name, \
					'Skeleton','Skeleton ' + str(self.counter + i)+'.xml'),self.player_1_id,self.player_2_id)
			pose_p1[i,:,:] = get_pose_numpy_array(p1)
			p2 = get_pose_numpy_array(p2, get_2d = True)
			pose_p2[i,:,:,:] = get_gaussian_gt(p2,self.sigma,self.h,self.w)

		self.counter += 1
		return pose_p2.astype(np.float32),pose_p2[::-1,:,:,:].astype(np.float32)

	def __len__(self):
		if self.reverse_player:
			return 2*self.total_data_num*self.epoch
		return self.total_data_num*self.epoch






