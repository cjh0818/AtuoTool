#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @author: cjh
# @datetime: 2025-09-02 14:38
# @filename: match_image.py
# @description: 图像模板匹配模块，提供多种图像处理和匹配算法

import cv2
import numpy as np
import pyautogui
from utils.logger import logger
from utils.exception_handler import ExceptionHandler, ElementNotFound

def preprocess_images(screenshot_cv, template):
    """
    图像预处理阶段：生成多种处理方法的图像版本
    :param screenshot_cv: 屏幕截图（BGR格式）
    :param template: 模板图像
    :return: 包含各种预处理图像和方法的元组列表
    """
    # 方法1：灰度图像匹配 - 基础的颜色去除方法，减少光照和颜色变化的影响
    screenshot_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    # 方法2：边缘检测匹配（Canny）- 专注于图像轮廓和形状特征，对颜色变化不敏感
    # 使用自适应阈值进行边缘检测，提高边缘检测的准确性
    screenshot_edges = cv2.Canny(screenshot_gray, 50, 150)
    template_edges = cv2.Canny(template_gray, 50, 150)
    
    # 方法3：直方图均衡化 - 增强图像对比度，突出细节特征
    screenshot_eq = cv2.equalizeHist(screenshot_gray)
    template_eq = cv2.equalizeHist(template_gray)
    
    return [
        ('灰度图像', screenshot_gray, template_gray),
        ('边缘检测', screenshot_edges, template_edges),
        ('直方图均衡化', screenshot_eq, template_eq)
    ]

def perform_template_matching(processed_images, methods, silent=False):
    """
    模板匹配阶段：使用多种方法和算法组合进行匹配
    :param processed_images: 预处理后的图像列表
    :param methods: 匹配方法列表
    :param silent: 静默模式
    :return: 所有匹配结果列表和最佳匹配结果
    """
    # 定义不同方法和算法组合的可靠性权重
    # 基于经验：灰度图像+TM_CCOEFF_NORMED通常最可靠，边缘检测次之，直方图均衡化可能产生异常
    method_reliability = {
        ('灰度图像', 'TM_CCOEFF_NORMED'): 1.0,      # 最高可靠性
        ('灰度图像', 'TM_CCORR_NORMED'): 0.9,
        ('灰度图像', 'TM_SQDIFF_NORMED'): 0.8,
        ('边缘检测', 'TM_CCOEFF_NORMED'): 0.85,
        ('边缘检测', 'TM_CCORR_NORMED'): 0.75,
        ('边缘检测', 'TM_SQDIFF_NORMED'): 0.7,
        ('直方图均衡化', 'TM_CCOEFF_NORMED'): 0.7,
        ('直方图均衡化', 'TM_CCORR_NORMED'): 0.6,
        ('直方图均衡化', 'TM_SQDIFF_NORMED'): 0.4   # 最低可靠性，容易产生异常
    }
    
    # 存储所有匹配结果用于一致性检查
    all_matches = []
    best_res = None
    best_score = -1
    best_method_name = ""
    best_img_name = ""
    best_location = None
    
    # 智能选择最佳结果：自动测试所有方法和算法组合
    logger.debug("开始多种图像处理方法和匹配算法的组合测试...")
    
    # 对每种图像处理方法和匹配方法进行尝试
    for img_name, screenshot_processed, template_processed in processed_images:
        for method_name, method in methods:
            try:
                # 使用当前方法和算法进行模板匹配
                res = cv2.matchTemplate(screenshot_processed, template_processed, method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                # 对于SQDIFF方法，最小值表示最佳匹配，需要转换为相似度分数
                if method == cv2.TM_SQDIFF_NORMED:
                    current_score = 1 - min_val  # 转换为相似度分数
                    current_loc = min_loc
                else:
                    current_score = max_val
                    current_loc = max_loc
                
                # 获取当前方法组合的可靠性权重
                reliability_weight = method_reliability.get((img_name, method_name), 0.5)
                
                # 计算加权分数（原始分数 × 可靠性权重）
                weighted_score = current_score * reliability_weight
                
                # 记录匹配结果时包含可靠性权重信息
                all_matches.append({
                    'score': current_score,
                    'weighted_score': weighted_score,
                    'location': current_loc,
                    'method': method_name,
                    'img_type': img_name,
                    'res': res,
                    'reliability': reliability_weight
                })
                
                # 使用加权分数选择最佳匹配结果
                if weighted_score > best_score:
                    best_score = weighted_score
                    best_res = res
                    best_method_name = method_name
                    best_img_name = img_name
                    best_location = current_loc
                    best_raw_score = current_score  # 保存原始分数用于日志输出
                    
                # 提供详细的匹配过程信息输出，包含可靠性权重
                logger.debug(f"方法: {img_name} + {method_name}, 匹配度: {current_score:.4f}, 可靠性: {reliability_weight:.1f}, 加权分数: {weighted_score:.4f}, 位置: {current_loc}")
                
            except Exception as e:
                log_func = logger.debug if silent else logger.error
                log_func(f"匹配方法 {img_name} + {method_name} 出错: {str(e)}")
                continue
    
    return all_matches, best_res, best_score, best_method_name, best_img_name, best_location, best_raw_score

def check_result_consistency(all_matches, min_confidence, template_shape, silent=False):
    """
    结果一致性检查阶段：使用聚类分析验证匹配结果的一致性
    :param all_matches: 所有匹配结果列表
    :param min_confidence: 最小置信度阈值
    :param template_shape: 模板图像的尺寸
    :param silent: 静默模式
    :return: 是否通过一致性检查
    """
    # 检查是否有多个高置信度匹配指向相似位置
    # 使用加权分数筛选高置信度匹配，但阈值适当降低以考虑权重影响
    high_confidence_matches = [m for m in all_matches if m['weighted_score'] >= min_confidence * 0.8]  # 使用更低的阈值筛选
    
    if len(high_confidence_matches) < 2:
        log_func = logger.debug if silent else logger.warning
        log_func(f"只有 {len(high_confidence_matches)} 个高置信度匹配，可能为误匹配")
        # 如果只有一个高置信度匹配，需要更严格的检查
        # 注意：这里需要访问外部变量，但由于我们保持逻辑不变，这个检查会在主函数中进行
        return False, high_confidence_matches
    
    # 改进的位置一致性检查 - 使用聚类分析而非简单平均距离
    # 方法1：使用中位数而非均值计算中心点，减少异常值影响
    locations = [m['location'] for m in high_confidence_matches]
    x_coords = [loc[0] for loc in locations]
    y_coords = [loc[1] for loc in locations]
    
    # 计算中位数中心点
    center_x = np.median(x_coords)
    center_y = np.median(y_coords)
    
    # 计算各位置与中心点的距离
    distances = [((loc[0] - center_x) ** 2 + (loc[1] - center_y) ** 2) ** 0.5 for loc in locations]
    
    # 方法2：使用距离的中位数而非均值，更加鲁棒
    median_distance = np.median(distances)
    
    # 方法3：识别并排除异常值（距离超过中位数2倍的点）
    filtered_locations = []
    outlier_count = 0
    for i, loc in enumerate(locations):
        if distances[i] <= median_distance * 2:  # 保留距离在中位数2倍范围内的点
            filtered_locations.append(loc)
        else:
            outlier_count += 1
            log_func = logger.debug if silent else logger.warning
            log_func(f"排除异常匹配位置: {loc}，距离: {distances[i]:.1f}，方法: {high_confidence_matches[i]['method']} + {high_confidence_matches[i]['img_type']}")
    
    # 如果过滤后的位置太少，说明匹配结果不一致
    if len(filtered_locations) < 2 and outlier_count > 0:
        log_func = logger.debug if silent else logger.warning
        log_func(f"过滤异常值后剩余匹配位置不足（剩余: {len(filtered_locations)}，排除: {outlier_count}），可能为误匹配")
        return False, high_confidence_matches
    
    # 重新计算过滤后的平均距离
    if len(filtered_locations) >= 2:
        filtered_center_x = sum(loc[0] for loc in filtered_locations) / len(filtered_locations)
        filtered_center_y = sum(loc[1] for loc in filtered_locations) / len(filtered_locations)
        avg_distance = sum(((loc[0] - filtered_center_x) ** 2 + (loc[1] - filtered_center_y) ** 2) ** 0.5 for loc in filtered_locations) / len(filtered_locations)
        
        # 使用更宽松的距离阈值（模板尺寸的1.5倍）
        max_allowed_distance = max(template_shape[0], template_shape[1]) * 1.5
        if avg_distance > max_allowed_distance:
            log_func = logger.debug if silent else logger.warning
            log_func(f"匹配位置过于分散（过滤后平均距离: {avg_distance:.1f}），可能为误匹配")
            return False, high_confidence_matches
    else:
        # 如果过滤后只剩一个位置，使用该位置作为结果
        logger.debug(f"过滤异常值后只剩一个匹配位置，使用该位置: {filtered_locations[0] if filtered_locations else 'None'}")
    
    return True, high_confidence_matches

def perform_secondary_verification(screenshot_processed, template_processed, best_location, min_confidence, silent=False):
    """
    二次验证阶段：在最佳匹配位置周围进行验证
    :param screenshot_processed: 处理后的屏幕截图
    :param template_processed: 处理后的模板图像
    :param best_location: 最佳匹配位置
    :param min_confidence: 最小置信度阈值
    :param silent: 静默模式
    :return: 是否通过二次验证
    """
    try:
        # 在最佳匹配位置周围提取小区域进行二次验证
        h, w = template_processed.shape[:2]
        x, y = best_location
        
        # 确保坐标不超出图像边界
        x = max(0, min(x, screenshot_processed.shape[1] - w))
        y = max(0, min(y, screenshot_processed.shape[0] - h))
        
        # 提取匹配区域
        matched_region = screenshot_processed[y:y+h, x:x+w]
        
        # 计算匹配区域与模板的相似度
        if matched_region.shape == template_processed.shape:
            # 使用归一化相关系数进行二次验证
            verification_score = cv2.matchTemplate(matched_region, template_processed, cv2.TM_CCOEFF_NORMED)[0, 0]
            
            # 如果二次验证分数过低，拒绝匹配
            verification_threshold = min_confidence * 0.8  # 二次验证使用稍低的阈值
            if verification_score < verification_threshold:
                log_func = logger.debug if silent else logger.warning
                log_func(f"二次验证失败，验证分数: {verification_score:.4f}，低于阈值: {verification_threshold}")
                return False
            
            logger.debug(f"二次验证通过，验证分数: {verification_score:.4f}")
            return True
        else:
            log_func = logger.debug if silent else logger.warning
            log_func("匹配区域尺寸不匹配，跳过二次验证")
            return True
    
    except Exception as e:
        log_func = logger.debug if silent else logger.error
        log_func(f"二次验证过程出错: {str(e)}")
        # 二次验证失败不直接拒绝匹配，但记录警告
        return True

@ExceptionHandler.handle_element_not_found_with_context("图像模板匹配")
def match_image(image_path, min_confidence=0.8, silent=False):
    """
    图像模板匹配函数，使用多阶段验证提高准确性。
    严格的置信度阈值、多阶段验证、结果一致性检查、二次确认机制。
    :param image_path: 小图路径
    :param min_confidence: 最小匹配置信度阈值，低于此值认为未找到匹配（默认提高到0.85）
    :param silent: 静默模式，失败时返回None而不是抛出异常
    :return: (res, template) 或 None
    """
    # 使用pyautogui库截取当前屏幕的截图
    screenshot = pyautogui.screenshot()
    # 将截图转换为numpy数组，并从RGB颜色空间转换为BGR颜色空间（OpenCV使用的格式）
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    # 使用OpenCV读取模板图像文件
    template = cv2.imread(image_path)
    if template is None:
        if silent:
            logger.debug(f"未找到图片: {image_path}")
            return None
        raise ElementNotFound(element_name=image_path, message=f"未找到图片: {image_path}")
    
    # 第一阶段：图像预处理
    processed_images = preprocess_images(screenshot_cv, template)
    
    # 多种匹配算法融合 - 优先使用更可靠的算法
    methods = [
        ('TM_CCOEFF_NORMED', cv2.TM_CCOEFF_NORMED),  # 归一化相关系数匹配（最可靠）
        ('TM_SQDIFF_NORMED', cv2.TM_SQDIFF_NORMED),  # 归一化平方差匹配
        ('TM_CCORR_NORMED', cv2.TM_CCORR_NORMED)    # 归一化互相关匹配（容易误匹配，放在最后）
    ]
    
    # 第二阶段：模板匹配
    all_matches, best_res, best_score, best_method_name, best_img_name, best_location, best_raw_score = perform_template_matching(processed_images, methods, silent)
    
    # 检查是否有匹配结果
    if best_res is None:
        if silent:
            logger.debug("所有匹配方法都失败了")
            return None
        raise ElementNotFound(element_name=image_path, message="所有匹配方法都失败了")
    
    # 第三阶段：检查最佳匹配度是否达到最小置信度阈值
    if best_score < min_confidence:
        if silent:
            logger.debug(f"未找到足够匹配的目标，最佳加权匹配度: {best_score:.4f}，原始匹配度: {best_raw_score:.4f}，低于阈值: {min_confidence}")
            return None
        raise ElementNotFound(element_name=image_path, message=f"未找到足够匹配的目标，最佳加权匹配度: {best_score:.4f}，原始匹配度: {best_raw_score:.4f}，低于阈值: {min_confidence}")
    
    # 第四阶段：结果一致性检查
    consistency_passed, high_confidence_matches = check_result_consistency(all_matches, min_confidence, template.shape, silent)
    
    # 如果一致性检查失败，进行额外检查
    if not consistency_passed:
        if len(high_confidence_matches) < 2:
            # 如果只有一个高置信度匹配，需要更严格的检查
            if best_score < min_confidence + 0.05:  # 如果最佳匹配度不够高，拒绝
                if silent:
                    logger.debug(f"单一匹配但置信度不足，拒绝匹配。最佳匹配度: {best_score:.4f}")
                    return None
                raise ElementNotFound(element_name=image_path, message=f"单一匹配但置信度不足，拒绝匹配。最佳匹配度: {best_score:.4f}")
    
    # 第五阶段：二次验证
    # 获取最佳匹配方法对应的处理图像
    best_processed_img = None
    best_processed_template = None
    for img_name, screenshot_processed, template_processed in processed_images:
        if img_name == best_img_name:
            best_processed_img = screenshot_processed
            best_processed_template = template_processed
            break
    
    if best_processed_img is not None:
        verification_passed = perform_secondary_verification(best_processed_img, best_processed_template, best_location, min_confidence, silent)
        if not verification_passed:
            if silent:
                logger.debug("二次验证失败")
                return None
            raise ElementNotFound(element_name=image_path, message="二次验证失败")
    
    # 输出最终选择的最佳结果信息
    logger.debug(f"找到匹配目标！最佳方法: {best_img_name} + {best_method_name}")
    logger.debug(f"最佳加权匹配度: {best_score:.4f}，原始匹配度: {best_raw_score:.4f}")
    logger.debug(f"匹配位置: {best_location}")
    logger.debug(f"高置信度匹配数量: {len(high_confidence_matches)}")
    
    return (best_res, template)

