# -*- coding:utf-8 -*-
import numpy as np
import cv2, os, argparse
from glob import glob
from tqdm import tqdm

from plate_number import random_select, generate_plate_number_white, generate_plate_number_yellow_xue
from plate_number import generate_plate_number_black_gangao, generate_plate_number_black_shi, generate_plate_number_black_ling
from plate_number import generate_plate_number_blue, generate_plate_number_yellow_gua
from plate_number import letters, digits


def get_location_data(length=7, split_id=1, height=140):
    """
    获取车牌号码在底牌中的位置
    length: 车牌字符数，7，7为普通车牌、
    split_id: 分割空隙
    height: 车牌高度，对应单层和双层车牌
    """
    # 字符位置
    location_xy = np.zeros((length, 4), dtype=np.int32)

    # 单层车牌高度
    if height == 140:
        # 单层车牌，y轴坐标固定
        location_xy[:, 1] = 25
        location_xy[:, 3] = 115
        # 螺栓间隔
        step_split = 34
        # 字符间隔
        step_font = 12

        # 字符宽度
        width_font = 45
        for i in range(length):
            if i == 0:
                location_xy[i, 0] = 15
            elif i == split_id:
                location_xy[i, 0] = location_xy[i - 1, 2] + step_split
            else:
                location_xy[i, 0] = location_xy[i - 1, 2] + step_font
            # 新能源车牌

            location_xy[i, 2] = location_xy[i, 0] + width_font

    return location_xy


# 字符贴上底板
def copy_to_image_multi(img, font_img, bbox, bg_color, is_red):
    x1, y1, x2, y2 = bbox
    font_img = cv2.resize(font_img, (x2 - x1, y2 - y1))
    img_crop = img[y1: y2, x1: x2, :]

    if is_red:
        img_crop[font_img < 200, :] = [0, 0, 255]
    elif 'blue' in bg_color or 'black' in bg_color:
        img_crop[font_img < 200, :] = [255, 255, 255]
    else:
        img_crop[font_img < 200, :] = [0, 0, 0]
    return img


class MultiPlateGenerator:
    def __init__(self, adr_plate_model, adr_font):
        # 车牌底板路径
        self.adr_plate_model = adr_plate_model
        # 车牌字符路径
        self.adr_font = adr_font

        # 车牌字符图片，预存处理
        self.font_imgs = {}
        font_filenames = glob(os.path.join(adr_font, '*jpg'))
        for font_filename in font_filenames:
            font_img = cv2.imdecode(np.fromfile(font_filename, dtype=np.uint8), 0)

            if '140' in font_filename:
                font_img = cv2.resize(font_img, (45, 90))
            elif '220' in font_filename:
                font_img = cv2.resize(font_img, (65, 110))
            elif font_filename.split('_')[-1].split('.')[0] in letters + digits:
                font_img = cv2.resize(font_img, (43, 90))
            self.font_imgs[os.path.basename(font_filename).split('.')[0]] = font_img

        # 字符位置
        self.location_xys = {}
        for i in [7, 8]:
            for j in [1, 2, 4]:
                for k in [140, 220]:
                    self.location_xys['{}_{}_{}'.format(i, j, k)] = \
                        get_location_data(length=i, split_id=j, height=k)

    # 获取字符位置
    def get_location_multi(self, plate_number, height=140):
        length = len(plate_number)
        if '警' in plate_number:
            split_id = 1
        elif '使' in plate_number:
            split_id = 4
        else:
            split_id = 2
        return self.location_xys['{}_{}_{}'.format(length, split_id, height)]

    # 随机生成车牌号码，获取底板颜色、单双层
    def generate_plate_number(self):
        rate = 1
        if rate > 0.4:
            # 蓝牌
            plate_number = generate_plate_number_blue(length=7)


        # 车牌底板颜色
        bg_color = random_select(['blue'] + ['yellow'])

        # if len(plate_number) == 8:
        #     bg_color = random_select(['green_car'] * 10 + ['green_truck'])
        # elif len(set(plate_number) & set(['使', '领', '港', '澳'])) > 0:
        #     bg_color = 'black'
        # elif '警' in plate_number or plate_number[0] in letters:
        #     bg_color = 'white'
        # elif len(set(plate_number) & set(['学', '挂'])) > 0:
        #     bg_color = 'yellow'

        is_double = random_select([False] + [True] * 3)



        return plate_number, bg_color, is_double

    # 随机生成车牌图片
    def generate_plate(self, enhance=False):
        plate_number, bg_color, is_double = self.generate_plate_number()
        height = 140

        # 获取底板图片
        # print(plate_number, height, bg_color, is_double)
        number_xy = self.get_location_multi(plate_number, height)
        img_plate_model = cv2.imread(os.path.join(self.adr_plate_model, '{}_{}.PNG'.format(bg_color, height)))
        img_plate_model = cv2.resize(img_plate_model, (440 if len(plate_number) == 7 else 480, height))

        for i in range(len(plate_number)):

            if '{}_{}'.format(height, plate_number[i]) in self.font_imgs:
                font_img = self.font_imgs['{}_{}'.format(height, plate_number[i])]

            # 字符是否红色
            if (i == 0 and plate_number[0] in letters) or plate_number[i] in ['警', '使', '领']:
                is_red = True
            elif i == 1 and plate_number[0] in letters and np.random.random(1) > 0.5:
                # second letter of army plate
                is_red = True
            else:
                is_red = False

            if enhance:
                k = np.random.randint(1, 6)
                kernel = np.ones((k, k), np.uint8)
                if np.random.random(1) > 0.5:
                    font_img = np.copy(cv2.erode(font_img, kernel, iterations=1))
                else:
                    font_img = np.copy(cv2.dilate(font_img, kernel, iterations=1))

            # 贴上底板
            img_plate_model = copy_to_image_multi(img_plate_model, font_img,
                                                  number_xy[i, :], bg_color, is_red)

        img_plate_model = cv2.blur(img_plate_model, (3, 3))

        return img_plate_model, number_xy, plate_number, bg_color, is_double




def parse_args():
    parser = argparse.ArgumentParser(description='中国车牌生成器')
    parser.add_argument('--number', default=100, type=int, help='生成车牌数量')
    parser.add_argument('--save-adr', default='。/multi_val', help='车牌保存路径')
    args = parser.parse_args()
    return args


def mkdir(path):
    try:
        os.makedirs(path)
    except:
        pass


if __name__ == '__main__':
    args = parse_args()
    print(args)
    # 随机生成车牌
    print('save in {}'.format(args.save_adr))

    mkdir(args.save_adr)
    generator = MultiPlateGenerator('plate_model', 'font_model')

    for i in tqdm(range(args.number)):
        img, number_xy, gt_plate_number, bg_color, is_double = generator.generate_plate()
        print(gt_plate_number)
        # cv2.imwrite(os.path.join(args.save_adr, '{}_{}_{}.jpg'.format(gt_plate_number, bg_color, is_double)), img)
        cv2.imencode('.jpg', img)[1].tofile('{}.jpg'.format(gt_plate_number))