import pygame
import pygame.camera

pygame.init()
pygame.camera.init()

cam = pygame.camera.Camera(pygame.camera.list_cameras()[0])
cam.start()

screen = pygame.display.set_mode((640, 480))

running = True
while running:
    image = cam.get_image()
    screen.blit(image, (0, 0))
    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

cam.stop()
pygame.quit()