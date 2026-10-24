# 一帧图像里的目标检测结果（自定义消息）
# 约定：cx/cy 使用像素坐标，原点在图像左上角，x 向右、y 向下。

std_msgs/Header header      # 时间戳 + 坐标系（这里复用相机节点的 frame_id）

bool  found                 # 本帧是否检测到目标
float32 cx                  # 目标质心 x（像素）
float32 cy                  # 目标质心 y（像素）
float32 area                # 目标像素面积（像素个数）
float32 confidence          # 置信度 0~1，用「面积 / 期望面积」粗略估计
