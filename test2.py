#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NAO情感陪伴实验 - 官方ALAudioDevice能量检测版
实体机器人专用，无ALSoundDetection
"""

from naoqi import ALProxy
import time
import random

# ===================== 配置 =====================
ROBOT_IP = "169.254.75.59"
ROBOT_PORT = 9559

GLOBAL_TIMEOUT = 420
SILENCE_TIMEOUT = 10
MAX_RESPONSE = 3
SILENCE_COMPANION_TIME = 30
SPEECH_END_TIMEOUT = 2  # 静音2秒=说完
ENERGY_THRESHOLD = 600  # 实体建议：300~1200

# ===================== 全局服务 =====================
tts = None
motion = None
posture = None
leds = None
audioDevice = None  # 只用这个
start_time = None
response_count = 0

# ===================== 初始化（纯ALAudioDevice） =====================
def initialize_services():
    global tts, motion, posture, leds, audioDevice
    try:
        tts = ALProxy("ALTextToSpeech", ROBOT_IP, ROBOT_PORT)
        motion = ALProxy("ALMotion", ROBOT_IP, ROBOT_PORT)
        posture = ALProxy("ALRobotPosture", ROBOT_IP, ROBOT_PORT)
        leds = ALProxy("ALLeds", ROBOT_IP, ROBOT_PORT)

        # 官方：启用麦克风能量
        audioDevice = ALProxy("ALAudioDevice", ROBOT_IP, ROBOT_PORT)
        audioDevice.enableEnergyComputation()

        print("[OK] 初始化成功（ALAudioDevice能量检测）")
        return True
    except Exception as e:
        print("[ERROR] 初始化失败: %s" % str(e))
        return False

def wake_up_robot():
    try:
        motion.wakeUp()
        motion.setStiffnesses("Body", 1.0)
        print("[OK] 机器人已唤醒")
        return True
    except Exception as e:
        print("[ERROR] 唤醒失败: %s" % str(e))
        return False

# ===================== 辅助 =====================
def say(text):
    if tts:
        try:
            tts.say(text)
            print("[TTS] %s" % text)
        except Exception as e:
            print("[ERROR] TTS: %s" % str(e))

def set_led(color):
    if not leds:
        return
    try:
        if color == "blue":
            leds.fadeRGB("FaceLeds", 0, 0, 255, 1.0)
            print("[LED] blue")
        elif color == "green":
            leds.fadeRGB("FaceLeds", 0, 255, 0, 1.0)
            print("[LED] green")
        else:
            leds.off("FaceLeds")
    except Exception as e:
        print("[ERROR] LED: %s" % str(e))

def do_pose(pose_name):
    if not motion or not posture:
        return
    try:
        if pose_name == "empathy":
            posture.goToPosture("Sit", 0.5)
            time.sleep(0.5)
            motion.setAngles(["HeadPitch", "HeadYaw"], [0.2, 0.0], 0.2)
        elif pose_name == "breath":
            motion.setAngles(["LShoulderPitch","RShoulderPitch","LElbowRoll","RElbowRoll"],
                              [1.2,1.2,0.5,-0.5], 0.1)
            print("[POSE] 吸气")
            time.sleep(3)
            motion.setAngles(["LShoulderPitch","RShoulderPitch","LElbowRoll","RElbowRoll"],
                              [0.4,0.4,0.0,0.0], 0.1)
            print("[POSE] 呼气")
            time.sleep(3)
        elif pose_name == "closing":
            motion.setAngles(["LShoulderRoll","RShoulderRoll"], [0.5,-0.5], 0.2)
            time.sleep(1)
    except Exception as e:
        print("[ERROR] POSE: %s" % str(e))

# ===================== 【关键】ALAudioDevice能量检测：等用户说完 =====================
def wait_for_user_speech_complete():
    """
    只用ALAudioDevice.getFrontMicEnergy()
    1) 能量>阈值 → 开始说话
    2) 连续SPEECH_END_TIMEOUT秒能量<阈值 → 说完
    """
    print("[WAIT] 等待回应（能量阈值=%d）" % ENERGY_THRESHOLD)
    start = time.time()
    speech_started = False
    quiet_time = 0.0

    while time.time() - start < SILENCE_TIMEOUT:
        time.sleep(0.1)
        energy = audioDevice.getFrontMicEnergy()

        if not speech_started:
            if energy > ENERGY_THRESHOLD:
                print("[DETECT] 开始说话，能量=%d" % energy)
                speech_started = True
                quiet_time = 0.0
        else:
            if energy > ENERGY_THRESHOLD:
                quiet_time = 0.0
            else:
                quiet_time += 0.1
                if quiet_time >= SPEECH_END_TIMEOUT:
                    print("[DETECT] 说完（静音%.1fs）" % SPEECH_END_TIMEOUT)
                    return True

    if speech_started:
        print("[TIMEOUT] 说话超时，视为说完")
        return True
    else:
        print("[TIMEOUT] 无回应")
        return False

def check_global_timeout():
    return time.time() - start_time > GLOBAL_TIMEOUT

# ===================== 实验阶段 =====================
def empathy_opening():
    print("\n=== 阶段1：共情开场 ===")
    set_led("blue")
    do_pose("empathy")
    say("我注意到你现在可能感觉不太好。有时候看完那样的视频，心里会觉得沉重——这很正常。我在这里陪着你。")
    time.sleep(2)

def listening_invite():
    print("\n=== 阶段2：倾听邀请 ===")
    say("如果你想说说现在的感受，我会认真听。如果不想说，也没关系，我们可以安静地坐一会儿。")
    try:
        for _ in range(3):
            motion.angleInterpolation("HeadPitch", [0.15,0.05,0.0], [0.6,1.0,1.4], True)
            time.sleep(1)
    except:
        for _ in range(3):
            motion.setAngles(["HeadPitch"], [0.15], 0.3)
            time.sleep(0.3)
            motion.setAngles(["HeadPitch"], [0.0], 0.2)
            time.sleep(0.4)

def response_validation():
    print("\n=== 阶段3：回应验证 ===")
    global response_count
    response_count = 0
    empathy_responses = [
        "听起来你真的很难受。这种失去的感觉确实让人心痛，我能真切感受到你的难过。",
        "我知道此刻这种难受的感觉挥之不去，不用强迫自己好起来——允许自己难过，本身就是很重要的事。",
        "你愿意把这些感受说出来，已经非常勇敢了。不管这种难过还要持续多久，我都会一直陪着你。"
    ]

    while response_count < MAX_RESPONSE:
        if check_global_timeout():
            break

        responded = wait_for_user_speech_complete()

        if responded:
            print("[BRANCH] 用户说完，进行安慰")
            say(empathy_responses[response_count])
            do_pose("empathy")
            response_count += 1
            print("[INFO] 次数：%d/%d" % (response_count, MAX_RESPONSE))
        else:
            print("[BRANCH] 静默陪伴")
            say("没关系，如果你不想说话，我们就安静地待一会儿吧。")
            time.sleep(SILENCE_COMPANION_TIME)
            print("[INFO] 静默结束，进入阶段4")
            break

def positive_reframe():
    print("\n=== 阶段4：积极转向 ===")
    say("让我们一起做几次深呼吸。吸气……呼气……这种难过的感觉会过去的，就像天气有阴晴变化。你现在正处于雨天，但晴天会回来的。")
    for _ in range(3):
        do_pose("breath")

def closing():
    print("\n=== 阶段5：结束 ===")
    say("时间到了。谢谢你愿意和我分享这段时间。记住，感到难过并不代表你软弱。如果需要，你随时可以回来找我聊天。")
    do_pose("closing")
    set_led("green")

def reset_to_initial_posture():
    try:
        posture.goToPosture("StandInit", 0.5)
        time.sleep(1)
        motion.setAngles(["HeadPitch","HeadYaw"], [0.0,0.0],0.2)
        set_led("off")
        print("[OK] 复位完成")
    except Exception as e:
        print("[ERROR] 复位: %s" % str(e))

# ===================== 主 =====================
def main():
    global start_time
    start_time = time.time()
    empathy_opening()
    if check_global_timeout():
        closing(); reset_to_initial_posture(); return
    listening_invite()
    if check_global_timeout():
        closing(); reset_to_initial_posture(); return
    response_validation()
    if check_global_timeout():
        closing(); reset_to_initial_posture(); return
    positive_reframe()
    if check_global_timeout():
        closing(); reset_to_initial_posture(); return
    closing()
    reset_to_initial_posture()
    print("\n=== 实验结束 ===")

if __name__ == "__main__":
    if not initialize_services():
        exit(1)
    if not wake_up_robot():
        exit(1)
    try:
        main()
    except Exception as e:
        print("[ERROR]", e)
        reset_to_initial_posture()